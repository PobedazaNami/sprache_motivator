"""
Subtitle service: fetches YouTube subtitles via youtube-transcript-api,
with automatic fallback to public Invidious instances when YouTube blocks
the server IP (common on cloud/datacenter providers like Hetzner).

Fetch strategy:
  1. youtube-transcript-api (fast, direct)
  2. On RequestBlocked → Invidious public API (different server IPs)
  3. Error with clear message if both fail

Translates with Google Translate (gtx endpoint), optionally explains with OpenAI.
"""

import asyncio
import json
import logging
import re
import time
import xml.etree.ElementTree as ET
from typing import Optional

import aiohttp

from bot.config import settings
from bot.services.redis_service import redis_service

logger = logging.getLogger(__name__)

_TRANSLATE_URL = (
    "https://translate.googleapis.com/translate_a/single"
    "?client=gtx&sl={sl}&tl={tl}&dt=t&q={q}"
)

_LANG_PRIORITY = ["de", "de-DE", "en", "fr", "es", "it", "pt"]
_CHANNEL_FEED_URL = "https://www.youtube.com/feeds/videos.xml?user=KurzgesagtDE"

# Public Invidious instances — fallback when YouTube blocks the server IP.
# See https://docs.invidious.io/api/ for the captions endpoint spec.
_INVIDIOUS_INSTANCES = [
    "https://invidious.io.lol",
    "https://inv.nadeko.net",
    "https://invidious.fdn.fr",
    "https://iv.melmac.space",
    "https://invidious.privacyredirect.com",
]

# Simple in-memory cache: video_id -> (result_dict, timestamp)
_session_cache: dict[str, tuple[dict, float]] = {}
_CACHE_TTL = 600  # 10 minutes (in-memory L1)
_REDIS_SUBTITLE_TTL = 86400  # 24 hours  (Redis L2, shared across users)
_REDIS_CHANNEL_TTL = 1800  # 30 minutes (Redis L2)
_channel_videos_cache: tuple[list[dict], float] | None = None
_CHANNEL_CACHE_TTL = 1800  # 30 minutes (in-memory L1)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_YT_ID_RE = re.compile(
    r"(?:youtube\.com/(?:watch\?.*v=|embed/|v/)"
    r"|youtu\.be/)"
    r"([\w-]{11})"
)


def _extract_video_id(input_str: str) -> Optional[str]:
    """Return 11-char video ID from a YouTube URL or bare ID."""
    input_str = input_str.strip()
    m = _YT_ID_RE.search(input_str)
    if m:
        return m.group(1)
    if re.fullmatch(r"[\w-]{11}", input_str):
        return input_str
    return None


def _cues_from_transcript(raw: list) -> list[dict]:
    """Convert youtube-transcript-api format to flat cue list: {startMs, endMs, text}."""
    cues = []
    for item in raw:
        text = item.get("text", "").replace("\n", " ").strip()
        if not text:
            continue
        start: float = item.get("start", 0.0)
        dur: float = item.get("duration", 2.0)
        cues.append({"startMs": int(start * 1000), "endMs": int((start + dur) * 1000), "text": text})
    return cues


# ---------------------------------------------------------------------------
# WebVTT parser (used for Invidious captions)
# ---------------------------------------------------------------------------

_VTT_TIMESTAMP_RE = re.compile(
    r"(\d{2}:\d{2}:\d{2}[.,]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[.,]\d{3})"
)
_VTT_TAG_RE = re.compile(r"<[^>]+>")


def _ts_to_ms(ts: str) -> int:
    """'00:01:23.456' or '00:01:23,456' → milliseconds."""
    ts = ts.replace(",", ".")
    h, m, rest = ts.split(":")
    return int((int(h) * 3600 + int(m) * 60 + float(rest)) * 1000)


def _parse_vtt(vtt_text: str) -> list[dict]:
    """Parse WebVTT content into cue list: {startMs, endMs, text}."""
    cues: list[dict] = []
    for block in re.split(r"\n{2,}", vtt_text):
        lines = block.strip().splitlines()
        for i, line in enumerate(lines):
            m = _VTT_TIMESTAMP_RE.match(line)
            if m:
                start_ms = _ts_to_ms(m.group(1))
                end_ms = _ts_to_ms(m.group(2))
                text = " ".join(lines[i + 1 :])
                text = _VTT_TAG_RE.sub("", text).strip()
                if text:
                    cues.append({"startMs": start_ms, "endMs": end_ms, "text": text})
                break
    return cues


# ---------------------------------------------------------------------------
# Invidious fallback (called when YouTube blocks the server IP)
# ---------------------------------------------------------------------------


async def _fetch_via_invidious(video_id: str) -> tuple[list[dict], str, list[str]]:
    """
    Fetch subtitles via public Invidious API instances.
    Tries each instance in _INVIDIOUS_INSTANCES until one succeeds.

    Returns (cues, selected_language_code, all_language_codes).
    Raises RuntimeError with a user-facing message if all fail.

    API spec: https://docs.invidious.io/api/#get-apiv1captionsid
    """
    timeout = aiohttp.ClientTimeout(total=15)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        for instance in _INVIDIOUS_INSTANCES:
            try:
                # Step 1: list available caption tracks
                caps_url = f"{instance}/api/v1/captions/{video_id}"
                async with session.get(caps_url) as resp:
                    if resp.status != 200:
                        logger.debug("Invidious %s returned HTTP %d for captions list", instance, resp.status)
                        continue
                    data = await resp.json(content_type=None)

                captions: list[dict] = data.get("captions", [])
                if not captions:
                    # Video genuinely has no captions — no point trying other instances
                    raise RuntimeError("У цього відео субтитри вимкнені.")

                # Step 2: pick the best available language
                # Invidious uses either 'languageCode' or 'language_code'
                def _lang(cap: dict) -> str:
                    return cap.get("languageCode") or cap.get("language_code", "")

                all_langs = list(dict.fromkeys(_lang(c) for c in captions if _lang(c)))

                selected: dict | None = None
                for lang in _LANG_PRIORITY + all_langs:
                    for cap in captions:
                        if _lang(cap) == lang:
                            selected = cap
                            break
                    if selected:
                        break
                if not selected:
                    selected = captions[0]

                # Step 3: fetch VTT content using the URL from the API response
                cap_url_path: str = selected.get("url", "")
                if not cap_url_path:
                    continue
                vtt_url = f"{instance}{cap_url_path}"
                async with session.get(vtt_url) as resp:
                    if resp.status != 200:
                        continue
                    vtt_text = await resp.text()

                cues = _parse_vtt(vtt_text)
                if not cues:
                    logger.debug("Invidious %s returned empty VTT for %s", instance, video_id)
                    continue

                logger.info("Fetched subtitles via Invidious: %s (lang=%s)", instance, _lang(selected))
                return cues, _lang(selected), all_langs

            except RuntimeError:
                raise  # propagate "subtitles disabled" errors immediately
            except Exception as exc:
                logger.warning("Invidious instance %s failed: %s", instance, exc)
                continue

    raise RuntimeError(
        "YouTube заблокував сервер і жоден резервний сервіс не відповів. "
        "Спробуйте інше відео або повторіть пізніше."
    )


def _parse_channel_feed(xml_text: str, limit: int) -> list[dict]:
    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "yt": "http://www.youtube.com/xml/schemas/2015",
        "media": "http://search.yahoo.com/mrss/",
    }
    root = ET.fromstring(xml_text)
    items: list[dict] = []

    for entry in root.findall("atom:entry", ns)[:limit]:
        video_id = entry.findtext("yt:videoId", namespaces=ns)
        title = entry.findtext("atom:title", default="", namespaces=ns)
        published_at = entry.findtext("atom:published", default="", namespaces=ns)
        thumb = entry.find("media:group/media:thumbnail", ns)
        thumbnail_url = thumb.attrib.get("url", "") if thumb is not None else ""
        if not video_id or not title:
            continue
        items.append(
            {
                "videoId": video_id,
                "title": title,
                "publishedAt": published_at,
                "thumbnailUrl": thumbnail_url,
                "videoUrl": f"https://www.youtube.com/watch?v={video_id}",
            }
        )

    return items


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def list_channel_videos(limit: int = 12) -> list[dict]:
    global _channel_videos_cache

    # L1: in-memory
    if _channel_videos_cache:
        cached_items, cached_at = _channel_videos_cache
        if time.time() - cached_at < _CHANNEL_CACHE_TTL:
            return cached_items[:limit]

    # L2: Redis (shared across restarts and workers)
    try:
        if redis_service.redis:
            cached_json = await redis_service.get("subtitle:channel_videos")
            if cached_json:
                videos = json.loads(cached_json)
                _channel_videos_cache = (videos, time.time())
                logger.info("Channel videos loaded from Redis cache")
                return videos[:limit]
    except Exception as exc:
        logger.debug("Redis channel cache read failed: %s", exc)

    # Fetch from YouTube RSS
    async with aiohttp.ClientSession() as session:
        async with session.get(_CHANNEL_FEED_URL, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            if resp.status != 200:
                raise RuntimeError("Не вдалося завантажити список відео каналу.")
            xml_text = await resp.text()

    videos = _parse_channel_feed(xml_text, max(limit, 12))
    if not videos:
        raise RuntimeError("Канал не повернув жодного відео.")

    # Store in both caches
    _channel_videos_cache = (videos, time.time())
    try:
        if redis_service.redis:
            await redis_service.set("subtitle:channel_videos", json.dumps(videos), ex=_REDIS_CHANNEL_TTL)
    except Exception as exc:
        logger.debug("Redis channel cache write failed: %s", exc)

    return videos[:limit]


async def load_video_session(input_str: str, preferred_title: Optional[str] = None) -> dict:
    """
    Download subtitle metadata for a YouTube video.

    Strategy:
      1. Return from in-memory cache if fresh (10 min TTL).
      2. Try youtube-transcript-api (fast, direct YouTube access).
      3. On RequestBlocked (server IP banned by YouTube) → Invidious fallback.
      4. Cache and return result.

    Returns:
        {videoId, title, cues, selectedLanguage, availableLanguages}
    """
    video_id = _extract_video_id(input_str)
    if not video_id:
        raise ValueError("Не вдалося розпізнати YouTube URL або ID відео.")

    # --- Cache check (L1: in-memory, L2: Redis) ---
    cached = _session_cache.get(video_id)
    if cached:
        result, ts = cached
        if time.time() - ts < _CACHE_TTL:
            logger.info("Subtitle L1 cache hit for %s", video_id)
            return result
        del _session_cache[video_id]

    # L2: Redis — shared across all users
    try:
        if redis_service.redis:
            redis_key = f"subtitle:session:{video_id}"
            cached_json = await redis_service.get(redis_key)
            if cached_json:
                result = json.loads(cached_json)
                _session_cache[video_id] = (result, time.time())
                logger.info("Subtitle L2 (Redis) cache hit for %s", video_id)
                return result
    except Exception as exc:
        logger.debug("Redis subtitle cache read failed: %s", exc)

    # --- Fetch subtitles ---
    from youtube_transcript_api import YouTubeTranscriptApi  # noqa: PLC0415
    from youtube_transcript_api._errors import RequestBlocked, TranscriptsDisabled  # noqa: PLC0415

    def _fetch_direct() -> tuple[list[dict], str, list[str]]:
        """Synchronous fetch via youtube-transcript-api (runs in thread executor)."""
        api = YouTubeTranscriptApi()
        transcript_list = api.list(video_id)
        all_langs = list(dict.fromkeys(t.language_code for t in transcript_list))
        try:
            transcript = transcript_list.find_transcript(_LANG_PRIORITY + all_langs)
        except Exception:
            raise RuntimeError("Для цього відео не знайдено субтитрів.")
        cues = _cues_from_transcript(transcript.fetch().to_raw_data())
        return cues, transcript.language_code, all_langs

    cues: list[dict]
    selected_lang: str
    all_langs: list[str]

    try:
        loop = asyncio.get_event_loop()
        cues, selected_lang, all_langs = await loop.run_in_executor(None, _fetch_direct)
    except TranscriptsDisabled:
        raise RuntimeError("У цього відео субтитри вимкнені.")
    except RequestBlocked:
        # YouTube bans datacenter/cloud IPs regularly.
        # Retrying the same blocked IP is pointless — go straight to Invidious.
        logger.warning("YouTube blocked this server IP for video %s — switching to Invidious fallback", video_id)
        cues, selected_lang, all_langs = await _fetch_via_invidious(video_id)
    except Exception as exc:
        raise RuntimeError(f"Не вдалося отримати субтитри: {exc}") from exc

    if not cues:
        raise RuntimeError("Субтитри порожні або не вдалося розібрати.")

    # --- Resolve title ---
    title = preferred_title or video_id
    if not preferred_title:
        try:
            oembed_url = (
                f"https://www.youtube.com/oembed"
                f"?url=https://www.youtube.com/watch?v={video_id}&format=json"
            )
            async with aiohttp.ClientSession() as sess:
                async with sess.get(oembed_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        data = await resp.json(content_type=None)
                        title = data.get("title", video_id)
        except Exception as exc:
            logger.warning("oEmbed title fetch failed: %s", exc)

    result = {
        "videoId": video_id,
        "title": title,
        "cues": cues,
        "selectedLanguage": selected_lang,
        "availableLanguages": all_langs,
    }

    # Store in both caches
    _session_cache[video_id] = (result, time.time())
    try:
        if redis_service.redis:
            redis_key = f"subtitle:session:{video_id}"
            await redis_service.set(redis_key, json.dumps(result), ex=_REDIS_SUBTITLE_TTL)
    except Exception as exc:
        logger.debug("Redis subtitle cache write failed: %s", exc)

    return result


async def translate_text(
    text: str,
    source_lang: str = "de",
    target_lang: str = "uk",
    *,
    session: Optional[aiohttp.ClientSession] = None,
    retries: int = 2,
) -> str:
    """Translate *text* using the public Google Translate gtx endpoint."""
    from urllib.parse import quote

    url = _TRANSLATE_URL.format(
        sl=source_lang, tl=target_lang, q=quote(text, safe="")
    )

    own_session = session is None
    if own_session:
        session = aiohttp.ClientSession()

    delay = 0.3
    try:
        for attempt in range(retries + 1):
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status != 200:
                        raise RuntimeError(f"HTTP {resp.status}")
                    data = await resp.json(content_type=None)
                    # data[0] is list of [translated, original, ...] pairs
                    result = "".join(
                        seg[0] for seg in data[0] if seg[0]
                    )
                    return result
            except Exception as exc:
                if attempt < retries:
                    await asyncio.sleep(delay)
                    delay *= 2
                    logger.warning("translate_text retry %d: %s", attempt + 1, exc)
                else:
                    raise
    finally:
        if own_session:
            await session.close()

    return text  # unreachable, but satisfies type checker


async def lookup_word(payload: dict) -> dict:
    """
    Translate and (optionally) explain a clicked word.

    Expected payload keys:
        surfaceForm, normalizedForm, cueText,
        previousCue (optional), nextCue (optional),
        videoLang (default "de"), targetLang (default "uk")

    Returns a WordCard dict.
    """
    surface: str = payload.get("surfaceForm", "")
    normalized: str = payload.get("normalizedForm", "") or surface
    cue_text: str = payload.get("cueText", "")
    prev_cue: str = payload.get("previousCue", "")
    next_cue: str = payload.get("nextCue", "")
    video_lang: str = payload.get("videoLang", "de")
    target_lang: str = payload.get("targetLang", "uk")

    async with aiohttp.ClientSession() as session:
        # 1. Translate the sentence the word appears in
        cue_translation = ""
        if cue_text:
            try:
                cue_translation = await translate_text(
                    cue_text, video_lang, target_lang, session=session
                )
            except Exception as exc:
                logger.warning("cue translation failed: %s", exc)
            await asyncio.sleep(0.15)

        # 2. Translate the word itself
        word_translation = ""
        try:
            word_translation = await translate_text(
                normalized, video_lang, target_lang, session=session
            )
        except Exception as exc:
            logger.warning("word translation failed: %s", exc)

    # 3. Optional OpenAI explanation
    explanation = ""
    if settings.OPENAI_API_KEY:
        context_parts = [p for p in [prev_cue, cue_text, next_cue] if p]
        context_text = " … ".join(context_parts)
        try:
            explanation = await _openai_explain(
                word=normalized,
                translation=word_translation,
                context=context_text,
                video_lang=video_lang,
                target_lang=target_lang,
            )
        except Exception as exc:
            logger.warning("OpenAI explanation failed: %s", exc)

    return {
        "surfaceForm": surface,
        "normalizedForm": normalized,
        "translation": word_translation,
        "cueText": cue_text,
        "cueTranslation": cue_translation,
        "explanation": explanation,
        "videoLang": video_lang,
        "targetLang": target_lang,
    }


async def _openai_explain(
    word: str,
    translation: str,
    context: str,
    video_lang: str,
    target_lang: str,
) -> str:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    lang_names = {"de": "German", "en": "English", "fr": "French",
                  "es": "Spanish", "it": "Italian"}
    target_names = {"uk": "Ukrainian", "ru": "Russian", "en": "English"}

    src_name = lang_names.get(video_lang, video_lang)
    tgt_name = target_names.get(target_lang, target_lang)

    system_prompt = (
        f"You are a language teacher helping a student learn {src_name}. "
        f"Give a brief, clear explanation of the word in {tgt_name}. "
        "Include: part of speech, any irregular forms (for verbs — infinitive; "
        "for nouns — gender and plural if relevant), and a usage note if helpful. "
        "Keep it to 2-3 short sentences."
    )

    user_prompt = (
        f'Word: "{word}" (translation: "{translation}")\n'
        f"Context: {context}"
    )

    resp = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        max_tokens=200,
        temperature=0.4,
    )
    return resp.choices[0].message.content.strip()
