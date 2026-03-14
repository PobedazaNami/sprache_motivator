"""
Subtitle service: fetches YouTube subtitles via yt-dlp,
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


def _parse_json3(data: dict) -> list[dict]:
    """
    Convert yt-dlp JSON3 subtitle format to a flat list of cue dicts.
    Each cue: {start, end, text}  (times in seconds as float)
    """
    cues = []
    for event in data.get("events", []):
        segs = event.get("segs")
        if not segs:
            continue
        text = "".join(s.get("utf8", "") for s in segs).strip()
        text = text.replace("\n", " ").strip()
        if not text:
            continue
        start_ms: int = event.get("tStartMs", 0)
        dur_ms: int = event.get("dDurationMs", 2000)
        cues.append(
            {
                "start": start_ms / 1000.0,
                "end": (start_ms + dur_ms) / 1000.0,
                "text": text,
            }
        )
    return cues


_LANG_PRIORITY = ["de", "en", "fr", "es", "it", "pt"]


def _pick_language(subs_info: dict) -> Optional[str]:
    """Pick the best available manual subtitle language."""
    available = list(subs_info.keys())
    if not available:
        return None
    for lang in _LANG_PRIORITY:
        if lang in available:
            return lang
    return available[0]


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

    url = f"https://www.youtube.com/watch?v={video_id}"

    try:
        import yt_dlp  # noqa: PLC0415
    except ImportError:
        raise RuntimeError(
            "Бібліотека yt-dlp не встановлена. Додайте yt-dlp до requirements.txt."
        )

    # Collected subtitle data: lang_code → json3 dict
    json3_by_lang: dict[str, dict] = {}
    meta: dict = {}

    def _ydl_progress_hook(d: dict) -> None:
        pass  # silence output

    # Use android + ios clients to bypass YouTube bot-detection on servers.
    # Fallback to web if needed. Optional cookies file via env var.
    import os as _os
    cookies_file = _os.environ.get("YOUTUBE_COOKIES_FILE", "")

    ydl_opts: dict = {
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": ["all"],
        "subtitlesformat": "json3",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "progress_hooks": [_ydl_progress_hook],
        # tv_embedded + ios bypass YouTube bot-detection on headless servers
        "extractor_args": {
            "youtube": {
                "player_client": ["tv_embedded", "ios", "android"],
            }
        },
    }
    if cookies_file and _os.path.exists(cookies_file):
        ydl_opts["cookiefile"] = cookies_file

    # Run blocking yt_dlp in thread pool to avoid blocking the event loop
    def _extract_sync() -> dict:
        collected: dict[str, dict] = {}
        info: dict = {}

        class _SubCollector(yt_dlp.YoutubeDL):
            pass

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                return {"info": {}, "subs": {}}

            # Merge manual + automatic subtitles
            all_subs: dict = {}
            all_subs.update(info.get("subtitles") or {})
            # Prefer manual; auto-subs prefixed with "xx-orig" — use plain codes
            for lang, data in (info.get("automatic_captions") or {}).items():
                clean_lang = lang.split("-")[0]  # "de-orig" → "de"
                if clean_lang not in all_subs:
                    all_subs[clean_lang] = data

            for lang, formats in all_subs.items():
                for fmt in (formats or []):
                    if fmt.get("ext") == "json3" and fmt.get("url"):
                        collected[lang] = fmt  # {url, ext, ...}
                        break

        return {"info": info, "subs": collected}

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, _extract_sync)

    info = result["info"]
    title = info.get("title", video_id) if info else video_id
    sub_formats = result["subs"]  # lang → {url, ext}

    if not sub_formats:
        raise RuntimeError("Для цього відео не знайдено субтитрів.")

    selected_lang = _pick_language(sub_formats)
    if not selected_lang:
        raise RuntimeError("Не вдалося вибрати мову субтитрів.")

    # Fetch the json3 subtitle file
    sub_url = sub_formats[selected_lang]["url"]
    async with aiohttp.ClientSession() as sess:
        async with sess.get(sub_url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            if resp.status != 200:
                raise RuntimeError(f"Не вдалося завантажити субтитри (HTTP {resp.status}).")
            raw = await resp.json(content_type=None)

    cues = _parse_json3(raw)
    if not cues:
        raise RuntimeError("Субтитри порожні або не вдалося розібрати.")

    return {
        "videoId": video_id,
        "title": title,
        "cues": cues,
        "selectedLanguage": selected_lang,
        "availableLanguages": list(sub_formats.keys()),
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
