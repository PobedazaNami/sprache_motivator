"""
Subtitle service: fetches YouTube subtitles via yt-dlp.

Fetch strategy:
  1. Check in-memory L1 cache (10 min TTL)
  2. Check Redis L2 cache (shared across all users, 7-day TTL)
  3. yt-dlp with cookie-authenticated requests
     (cookies loaded from /app/cookies/youtube_cookies.txt)

Background cache warmer:
  - Runs at startup
  - Fetches subtitles for channel videos one at a time with delays

Translates with Google Translate (gtx endpoint), optionally explains with OpenAI.
"""

import asyncio
import json
import logging
import os
import re
import shutil
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

# Simple in-memory cache: video_id -> (result_dict, timestamp)
_session_cache: dict[str, tuple[dict, float]] = {}
_CACHE_TTL = 600  # 10 minutes (in-memory L1)
_REDIS_SUBTITLE_TTL = 604800  # 7 days  (Redis L2, shared across users)
_REDIS_CHANNEL_TTL = 1800  # 30 minutes (Redis L2)
_channel_videos_cache: tuple[list[dict], float] | None = None
_CHANNEL_CACHE_TTL = 1800  # 30 minutes (in-memory L1)
_WARM_DELAY = 20  # seconds between subtitle fetches during cache warming
_warmer_running = False
_COOKIE_PATH = os.environ.get("YOUTUBE_COOKIE_PATH", "/app/cookies/youtube_cookies.txt")

# Per-video locks: prevents thundering herd (60 users click same video →
# only 1 request goes to YouTube, others wait for result from cache).
_video_locks: dict[str, asyncio.Lock] = {}


def _get_video_lock(video_id: str) -> asyncio.Lock:
    """Get or create an asyncio.Lock for a specific video_id."""
    if video_id not in _video_locks:
        _video_locks[video_id] = asyncio.Lock()
    return _video_locks[video_id]

# ---------------------------------------------------------------------------
# yt-dlp subtitle extraction
# ---------------------------------------------------------------------------

_COOKIE_TMP = "/tmp/yt_cookies.txt"


def _ensure_cookie_copy() -> str | None:
    """Copy cookies to writable location (yt-dlp needs write access). Returns path or None."""
    if not os.path.isfile(_COOKIE_PATH):
        logger.warning("Cookie file not found at %s", _COOKIE_PATH)
        return None
    try:
        shutil.copy2(_COOKIE_PATH, _COOKIE_TMP)
        return _COOKIE_TMP
    except Exception as exc:
        logger.error("Failed to copy cookies: %s", exc)
        return None


def _fetch_subtitles_ytdlp(video_id: str) -> tuple[list[dict], str, list[str]]:
    """Fetch subtitles via yt-dlp (synchronous, runs in thread executor).

    Returns (cues, selected_language, available_languages).
    """
    import yt_dlp  # noqa: PLC0415

    cookie_path = _ensure_cookie_copy()
    ydl_opts: dict = {
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": _LANG_PRIORITY,
        "subtitlesformat": "json3",
        "quiet": True,
        "no_warnings": True,
        "ignore_no_formats_error": True,
    }
    if cookie_path:
        ydl_opts["cookiefile"] = cookie_path

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(
            f"https://www.youtube.com/watch?v={video_id}", download=False
        )

    subs = info.get("subtitles", {})
    auto_subs = info.get("automatic_captions", {})
    all_langs = list(dict.fromkeys(list(subs.keys()) + list(auto_subs.keys())))

    # Try languages in priority order
    import requests as _requests  # noqa: PLC0415

    for lang in _LANG_PRIORITY + all_langs:
        sub_list = subs.get(lang, []) or auto_subs.get(lang, [])
        if not sub_list:
            continue
        json3_entries = [s for s in sub_list if s.get("ext") == "json3"]
        if not json3_entries:
            continue
        url = json3_entries[0]["url"]
        resp = _requests.get(url, timeout=15)
        if resp.status_code != 200:
            continue
        data = resp.json()
        events = data.get("events", [])
        cues = _cues_from_json3_events(events)
        if cues:
            return cues, lang, all_langs

    return [], "", all_langs


def _cues_from_json3_events(events: list[dict]) -> list[dict]:
    """Convert yt-dlp json3 events to flat cue list with word-level timing."""
    cues = []
    for event in events:
        segs = event.get("segs", [])
        text = "".join(s.get("utf8", "") for s in segs).replace("\n", " ").strip()
        if not text:
            continue
        start_ms = event.get("tStartMs", 0)
        dur_ms = event.get("dDurationMs", 2000)

        # Extract per-word timing from segments
        words = []
        for seg in segs:
            w = seg.get("utf8", "").replace("\n", " ").strip()
            if not w:
                continue
            offset = seg.get("tOffsetMs", 0)
            words.append({"w": w, "s": start_ms + offset})

        cue: dict = {"startMs": start_ms, "endMs": start_ms + dur_ms, "text": text}
        if words:
            cue["words"] = words
        cues.append(cue)
    return cues


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


# ---------------------------------------------------------------------------
# Background cache warmer
# ---------------------------------------------------------------------------


async def _fetch_and_cache_one(video_id: str, title: str) -> bool:
    """
    Try to fetch subtitles for one video and store in Redis.
    Returns True if cached successfully, False if blocked/failed.
    """
    try:
        loop = asyncio.get_event_loop()
        cues, selected_lang, all_langs = await loop.run_in_executor(
            None, _fetch_subtitles_ytdlp, video_id
        )
    except Exception as exc:
        logger.warning("Cache warmer fetch failed for %s: %s", video_id, exc)
        return False

    if not cues:
        return False

    result = {
        "videoId": video_id,
        "title": title,
        "cues": cues,
        "selectedLanguage": selected_lang,
        "availableLanguages": all_langs,
    }

    _session_cache[video_id] = (result, time.time())
    try:
        if redis_service.redis:
            redis_key = f"subtitle:session:{video_id}"
            await redis_service.set(redis_key, json.dumps(result), ex=_REDIS_SUBTITLE_TTL)
    except Exception:
        pass

    return True


async def warm_subtitle_cache() -> None:
    """
    Background task: fetch subtitles for all channel videos that aren't
    yet in Redis. YouTube allows ~1-2 requests before IP block, so we
    fetch slowly (20s delay). Runs at startup and can be called periodically.
    """
    global _warmer_running
    if _warmer_running:
        return
    _warmer_running = True

    try:
        videos = await list_channel_videos(limit=15)
        cached_count = 0
        fetched_count = 0

        for video in videos:
            vid = video["videoId"]
            # Check if already in Redis
            try:
                if redis_service.redis:
                    existing = await redis_service.get(f"subtitle:session:{vid}")
                    if existing:
                        cached_count += 1
                        continue
            except Exception:
                pass

            # Not cached — try to fetch
            if fetched_count > 0:
                await asyncio.sleep(_WARM_DELAY)

            ok = await _fetch_and_cache_one(vid, video.get("title", vid))
            if ok:
                fetched_count += 1
                logger.info("Cache warmer: cached subtitles for %s", vid)
            else:
                logger.warning("Cache warmer: failed for video %s, continuing", vid)

        logger.info("Cache warmer done: %d already cached, %d newly fetched, %d total videos",
                    cached_count, fetched_count, len(videos))
    except Exception as exc:
        logger.warning("Cache warmer error: %s", exc)
    finally:
        _warmer_running = False


async def get_cached_video_ids() -> set[str]:
    """Return set of video IDs that have subtitles in Redis."""
    result: set[str] = set()
    try:
        videos = await list_channel_videos(limit=15)
        for video in videos:
            vid = video["videoId"]
            if vid in _session_cache:
                result.add(vid)
                continue
            if redis_service.redis:
                existing = await redis_service.get(f"subtitle:session:{vid}")
                if existing:
                    result.add(vid)
    except Exception:
        pass
    return result


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
      2. Return from Redis L2 cache (7-day TTL).
      3. Fetch via youtube-transcript-api with cookie authentication.
      4. Cache result in L1 + L2.

    Returns:
        {videoId, title, cues, selectedLanguage, availableLanguages}
    """
    video_id = _extract_video_id(input_str)
    if not video_id:
        raise ValueError("Не вдалося розпізнати YouTube URL або ID відео.")

    # --- Fast path: L1 in-memory cache (no lock needed) ---
    cached = _session_cache.get(video_id)
    if cached:
        result, ts = cached
        if time.time() - ts < _CACHE_TTL:
            logger.info("Subtitle L1 cache hit for %s", video_id)
            return result
        del _session_cache[video_id]

    # --- Lock per video: thundering herd protection ---
    # If 60 users click the same video, only 1 goes to YouTube.
    # The other 59 wait here and get the result from cache.
    lock = _get_video_lock(video_id)
    async with lock:
        # Re-check caches after acquiring lock (another coroutine may have filled them)
        cached = _session_cache.get(video_id)
        if cached:
            result, ts = cached
            if time.time() - ts < _CACHE_TTL:
                logger.info("Subtitle L1 cache hit (post-lock) for %s", video_id)
                return result

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

        # --- Fetch subtitles (only 1 coroutine reaches here per video) ---
        cues: list[dict]
        selected_lang: str
        all_langs: list[str]

        try:
            loop = asyncio.get_event_loop()
            cues, selected_lang, all_langs = await loop.run_in_executor(
                None, _fetch_subtitles_ytdlp, video_id
            )
        except Exception as exc:
            logger.warning("yt-dlp fetch failed for video %s: %s", video_id, exc)
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
