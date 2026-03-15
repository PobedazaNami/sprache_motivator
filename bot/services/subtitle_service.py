"""
Subtitle service: fetches YouTube subtitles via Invidious public API
(fallback: youtube-transcript-api),
translates with Google Translate (gtx endpoint), and
optionally explains with OpenAI.
"""

import asyncio
import json
import logging
import os
import re
from typing import Optional
from urllib.parse import quote

import aiohttp

from bot.config import settings

logger = logging.getLogger(__name__)

_TRANSLATE_URL = (
    "https://translate.googleapis.com/translate_a/single"
    "?client=gtx&sl={sl}&tl={tl}&dt=t&q={q}"
)

_LANG_PRIORITY = ["de", "de-DE", "en", "fr", "es", "it", "pt"]

_DEFAULT_INVIDIOUS_INSTANCES = [
    "https://vid.puffyan.us",
    "https://inv.nadeko.net",
    "https://invidious.fdn.fr",
    "https://invidious.privacyredirect.com",
    "https://iv.nbooo.de",
]


def _get_invidious_instances() -> list[str]:
    raw = os.environ.get("INVIDIOUS_INSTANCES", "")
    if raw:
        try:
            instances = json.loads(raw)
            if isinstance(instances, list) and instances:
                return [s.rstrip("/") for s in instances]
        except json.JSONDecodeError:
            pass
    return list(_DEFAULT_INVIDIOUS_INSTANCES)

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


_VTT_TS_RE = re.compile(
    r"(\d{2}):(\d{2}):(\d{2})\.(\d{3})"
)


def _vtt_ts_to_ms(ts: str) -> int:
    m = _VTT_TS_RE.search(ts)
    if not m:
        return 0
    h, mi, s, ms = (int(g) for g in m.groups())
    return h * 3600000 + mi * 60000 + s * 1000 + ms


def _parse_vtt(text: str) -> list[dict]:
    """Parse WebVTT text into cue list {startMs, endMs, text}."""
    cues: list[dict] = []
    blocks = re.split(r"\n\n+", text.strip())
    for block in blocks:
        lines = block.strip().splitlines()
        # Find the line with the timestamp arrow
        ts_idx = -1
        for i, line in enumerate(lines):
            if "-->" in line:
                ts_idx = i
                break
        if ts_idx < 0:
            continue
        parts = lines[ts_idx].split("-->")
        if len(parts) < 2:
            continue
        start_ms = _vtt_ts_to_ms(parts[0].strip())
        end_ms = _vtt_ts_to_ms(parts[1].strip())
        content = " ".join(lines[ts_idx + 1:]).replace("\n", " ").strip()
        # Strip VTT tags like <c> </c> etc.
        content = re.sub(r"<[^>]+>", "", content).strip()
        if not content:
            continue
        cues.append({"startMs": start_ms, "endMs": end_ms, "text": content})
    return cues


def _is_german(label: str) -> bool:
    return bool(re.search(r"(^de$|^de-|deutsch|german)", label, re.IGNORECASE))


async def _fetch_captions_invidious(video_id: str) -> dict:
    """
    Fetch subtitles via Invidious public API.
    Tries multiple instances; picks German track.

    Returns:
        {videoId, title, cues, selectedLanguage, availableLanguages}
    """
    instances = _get_invidious_instances()
    last_error: Exception | None = None

    async with aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=15)
    ) as sess:
        for instance in instances:
            try:
                # 1. List caption tracks
                list_url = f"{instance}/api/v1/captions/{video_id}"
                async with sess.get(list_url) as resp:
                    if resp.status != 200:
                        logger.debug("Invidious %s returned %s", instance, resp.status)
                        continue
                    data = await resp.json(content_type=None)

                tracks = data.get("captions") or []
                if not tracks:
                    raise RuntimeError("У цього відео немає доступних субтитрів.")

                available = [t.get("label", t.get("language_code", "")) for t in tracks]

                # 2. Find German track (prefer non-auto over auto)
                german_tracks = [t for t in tracks if _is_german(
                    t.get("language_code", "") + " " + t.get("label", "")
                )]
                if not german_tracks:
                    raise RuntimeError(
                        f"Для цього відео немає німецьких субтитрів. "
                        f"Доступні: {', '.join(available)}"
                    )
                # Prefer non-auto-generated
                track = next(
                    (t for t in german_tracks if "auto" not in t.get("label", "").lower()),
                    german_tracks[0],
                )

                label = track.get("label", "")

                # 3. Fetch caption content (VTT)
                caption_url = f"{instance}/api/v1/captions/{video_id}?label={quote(label)}"
                async with sess.get(caption_url) as cresp:
                    if cresp.status != 200:
                        logger.debug("Invidious caption fetch %s returned %s", instance, cresp.status)
                        continue
                    vtt_text = await cresp.text()

                cues = _parse_vtt(vtt_text)
                if not cues:
                    raise RuntimeError("Субтитри порожні або не вдалося розібрати.")

                # 4. Title via oEmbed
                title = video_id
                try:
                    oembed_url = (
                        f"https://www.youtube.com/oembed"
                        f"?url=https://www.youtube.com/watch?v={video_id}&format=json"
                    )
                    async with sess.get(oembed_url, timeout=aiohttp.ClientTimeout(total=10)) as tresp:
                        if tresp.status == 200:
                            tdata = await tresp.json(content_type=None)
                            title = tdata.get("title", video_id)
                except Exception as exc:
                    logger.warning("oEmbed title fetch failed: %s", exc)

                return {
                    "videoId": video_id,
                    "title": title,
                    "cues": cues,
                    "selectedLanguage": track.get("language_code", "de"),
                    "availableLanguages": available,
                }

            except RuntimeError:
                raise
            except Exception as exc:
                logger.warning("Invidious instance %s failed: %s", instance, exc)
                last_error = exc
                continue

    raise RuntimeError(
        "Не вдалося отримати субтитри через Invidious. "
        + (str(last_error) if last_error else "Усі інстанси недоступні.")
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def load_video_session(input_str: str) -> dict:
    """
    Download subtitle metadata for a YouTube video.
    Primary: Invidious public API.
    Fallback: youtube-transcript-api (may fail on cloud IPs).

    Returns:
        {videoId, title, cues, selectedLanguage, availableLanguages}
    """
    video_id = _extract_video_id(input_str)
    if not video_id:
        raise ValueError("Не вдалося розпізнати YouTube URL або ID відео.")

    # --- Primary: Invidious ---
    try:
        return await _fetch_captions_invidious(video_id)
    except RuntimeError:
        raise
    except Exception as exc:
        logger.warning("Invidious failed, trying youtube-transcript-api: %s", exc)

    # --- Fallback: youtube-transcript-api ---
    try:
        from youtube_transcript_api import YouTubeTranscriptApi  # noqa: PLC0415
        from youtube_transcript_api.proxies import GenericProxyConfig  # noqa: PLC0415
    except ImportError:
        raise RuntimeError(
            "Бібліотека youtube-transcript-api не встановлена."
        )

    proxy_url = os.environ.get("YOUTUBE_PROXY_URL", "")

    def _build_api() -> YouTubeTranscriptApi:
        if proxy_url:
            return YouTubeTranscriptApi(
                proxy_config=GenericProxyConfig(
                    http_url=proxy_url,
                    https_url=proxy_url,
                )
            )
        return YouTubeTranscriptApi()

    def _fetch_sync() -> tuple[list[dict], str, list[str]]:
        api = _build_api()
        transcript_list = api.list(video_id)

        all_langs: list[str] = []
        seen: set[str] = set()
        for t in transcript_list:
            if t.language_code not in seen:
                all_langs.append(t.language_code)
                seen.add(t.language_code)

        try:
            transcript = transcript_list.find_transcript(_LANG_PRIORITY + all_langs)
        except Exception:
            raise RuntimeError("Для цього відео не знайдено субтитрів.")

        selected = transcript.language_code
        cues = _cues_from_transcript(transcript.fetch().to_raw_data())
        return cues, selected, all_langs

    loop = asyncio.get_event_loop()
    cues, selected_lang, all_langs = await loop.run_in_executor(None, _fetch_sync)

    if not cues:
        raise RuntimeError("Субтитри порожні або не вдалося розібрати.")

    title = video_id
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

    return {
        "videoId": video_id,
        "title": title,
        "cues": cues,
        "selectedLanguage": selected_lang,
        "availableLanguages": all_langs,
    }


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
