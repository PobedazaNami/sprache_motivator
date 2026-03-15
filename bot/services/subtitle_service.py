"""
Subtitle service: fetches YouTube subtitles via youtube-transcript-api
(public /api/timedtext endpoint — no auth required),
translates with Google Translate (gtx endpoint), and
optionally explains with OpenAI.
"""

import asyncio
import json
import logging
import re
from typing import Optional

import aiohttp

from bot.config import settings

logger = logging.getLogger(__name__)

_TRANSLATE_URL = (
    "https://translate.googleapis.com/translate_a/single"
    "?client=gtx&sl={sl}&tl={tl}&dt=t&q={q}"
)

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
    """Convert youtube-transcript-api format to flat cue list: {start, end, text}."""
    cues = []
    for item in raw:
        text = item.get("text", "").replace("\n", " ").strip()
        if not text:
            continue
        start: float = item.get("start", 0.0)
        dur: float = item.get("duration", 2.0)
        cues.append({"start": start, "end": start + dur, "text": text})
    return cues


def _parse_json3_caption(data: dict) -> list[dict]:
    """
    Parse YouTube JSON3 caption format into flat cue list {startMs, endMs, text}.
    The captionTrackUrl with &fmt=json3 returns this format.
    """
    cues = []
    for event in data.get("events", []):
        segs = event.get("segs")
        if not segs:
            continue
        text = "".join(s.get("utf8", "") for s in segs).replace("\n", " ").strip()
        if not text:
            continue
        start_ms: int = event.get("tStartMs", 0)
        dur_ms: int = event.get("dDurationMs", 2000)
        cues.append({
            "startMs": start_ms,
            "endMs": start_ms + dur_ms,
            "text": text,
        })
    return cues


async def load_session_from_caption_url(
    caption_url: str,
    video_id: str,
    lang: str,
    available_languages: list[str],
) -> dict:
    """
    Fetch subtitle cues using a signed captionTrackUrl obtained from the
    YouTube IFrame player running in the user's browser.

    This avoids all server-side YouTube scraping — we only download a single
    text file whose URL was provided by the browser.

    Args:
        caption_url: signed URL from player.getOption('captions','tracklist')
        video_id: 11-char YouTube video ID
        lang: language code e.g. 'de'
        available_languages: all available language codes from the player

    Returns:
        {videoId, title, cues, selectedLanguage, availableLanguages}
    """
    # Append fmt=json3 to get structured JSON instead of XML/VTT
    sep = "&" if "?" in caption_url else "?"
    fetch_url = caption_url + sep + "fmt=json3"

    async with aiohttp.ClientSession() as sess:
        # 1. Fetch caption JSON3
        async with sess.get(fetch_url, timeout=aiohttp.ClientTimeout(total=20)) as resp:
            if resp.status != 200:
                raise RuntimeError(
                    f"Не вдалося завантажити субтитри (HTTP {resp.status})."
                )
            raw = await resp.json(content_type=None)

        cues = _parse_json3_caption(raw)
        if not cues:
            raise RuntimeError("Субтитри порожні або не вдалося розібрати.")

        # 2. Fetch video title via oEmbed (public, always works)
        title = video_id
        try:
            oembed_url = (
                f"https://www.youtube.com/oembed"
                f"?url=https://www.youtube.com/watch?v={video_id}&format=json"
            )
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
        "selectedLanguage": lang,
        "availableLanguages": available_languages,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def load_video_session(input_str: str) -> dict:
    """
    Download subtitle metadata for a YouTube video.

    Returns:
        {videoId, title, cues, selectedLanguage, availableLanguages}

    Raises:
        ValueError – if the input is not a valid YouTube URL/ID
        RuntimeError – if yt-dlp fails or no subtitles are found
    """
    video_id = _extract_video_id(input_str)
    if not video_id:
        raise ValueError("Не вдалося розпізнати YouTube URL або ID відео.")

    try:
        from youtube_transcript_api import (  # noqa: PLC0415
            YouTubeTranscriptApi,
        )
        from youtube_transcript_api.proxies import GenericProxyConfig  # noqa: PLC0415
    except ImportError:
        raise RuntimeError(
            "Бібліотека youtube-transcript-api не встановлена. Додайте її до requirements.txt."
        )

    import os as _os
    proxy_url = _os.environ.get("YOUTUBE_PROXY_URL", "")

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

        # Collect all available language codes (manual first, then generated)
        all_langs: list[str] = []
        seen: set[str] = set()
        for t in transcript_list:
            if t.language_code not in seen:
                all_langs.append(t.language_code)
                seen.add(t.language_code)

        # find_transcript: prefers manually created over generated by default
        # Tries each language in priority order
        try:
            transcript = transcript_list.find_transcript(_LANG_PRIORITY + all_langs)
        except Exception:
            raise RuntimeError("Для цього відео не знайдено субтитрів.")

        selected = transcript.language_code
        # to_raw_data() returns [{text, start, duration}, ...]  (per docs)
        cues = _cues_from_transcript(transcript.fetch().to_raw_data())
        return cues, selected, all_langs

    loop = asyncio.get_event_loop()
    cues, selected_lang, all_langs = await loop.run_in_executor(None, _fetch_sync)

    if not cues:
        raise RuntimeError("Субтитри порожні або не вдалося розібрати.")

    # Fetch video title via YouTube oEmbed (public, no API key required)
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
