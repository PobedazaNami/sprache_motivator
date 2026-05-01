"""
Subtitle service: fetches YouTube subtitles via yt-dlp.

Fetch strategy:
  1. Check in-memory L1 cache (10 min TTL)
  2. Check Redis L2 cache (shared across all users, 7-day TTL)
  3. yt-dlp with cookie-authenticated requests
     (cookies loaded from /app/cookies/youtube_cookies.txt)

Background cache warmer:
  - Pins 20 Kurzgesagt DE videos into a shared catalog
  - Prepares subtitles for that fixed catalog in MongoDB/Redis

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
from datetime import datetime, timezone
from typing import Optional

import aiohttp

from bot.config import settings
from bot.services import mongo_service
from bot.services.redis_service import redis_service

logger = logging.getLogger(__name__)

_TRANSLATE_URL = (
    "https://translate.googleapis.com/translate_a/single"
    "?client=gtx&sl={sl}&tl={tl}&dt=t&q={q}"
)

_LANG_PRIORITY = ["de", "de-DE", "en", "fr", "es", "it", "pt"]
_CHANNEL_FEED_URL = "https://www.youtube.com/feeds/videos.xml?user=KurzgesagtDE"
_CHANNEL_VIDEOS_URL = "https://www.youtube.com/user/KurzgesagtDE/videos"
_FIXED_LIBRARY_SIZE = 20
_FIXED_LIBRARY_DOC_ID = "kurzgesagt_de_fixed_v1"
_REDIS_FIXED_LIBRARY_KEY = "subtitle:fixed_library:kurzgesagt_de:v1"
_REDIS_FIXED_LIBRARY_TTL = 604800  # 7 days

# Simple in-memory cache: video_id -> (result_dict, timestamp)
_session_cache: dict[str, tuple[dict, float]] = {}
_CACHE_TTL = 600  # 10 minutes (in-memory L1)
_REDIS_SUBTITLE_TTL = 604800  # 7 days  (Redis L2, shared across users)
_REDIS_CHANNEL_TTL = 1800  # 30 minutes (Redis L2)
_channel_videos_cache: tuple[list[dict], float] | None = None
_CHANNEL_CACHE_TTL = 1800  # 30 minutes (in-memory L1)
_WARM_DELAY = 20  # seconds between slow background fetches
_MIN_READY_LIBRARY_SIZE = _FIXED_LIBRARY_SIZE
_fixed_library_cache: list[dict] | None = None
_warmer_running = False
_warm_task: asyncio.Task | None = None
_bootstrap_task: asyncio.Task | None = None
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

        seen_langs = set()
        for lang in _LANG_PRIORITY + all_langs:
            if lang in seen_langs:
                continue
            seen_langs.add(lang)
            sub_list = subs.get(lang, []) or auto_subs.get(lang, [])
            if not sub_list:
                continue
            json3_entries = [s for s in sub_list if s.get("ext") == "json3"]
            if not json3_entries:
                continue
            url = json3_entries[0]["url"]
            try:
                # Use yt-dlp's opener so the timedtext request keeps the same
                # client headers/cookie handling that produced the subtitle URL.
                resp = ydl.urlopen(url)
                if getattr(resp, "status", 200) != 200:
                    logger.warning(
                        "Subtitle URL returned HTTP %s for %s (%s)",
                        getattr(resp, "status", "unknown"),
                        video_id,
                        lang,
                    )
                    continue
                data = json.loads(resp.read().decode("utf-8"))
            except Exception as exc:
                logger.warning("Subtitle URL fetch failed for %s (%s): %s", video_id, lang, exc)
                continue

            events = data.get("events", [])
            cues = _cues_from_json3_events(events)
            if cues:
                return cues, lang, all_langs

    return [], "", all_langs


def _cues_from_json3_events(events: list[dict]) -> list[dict]:
    """Convert yt-dlp json3 events to flat cue list: {startMs, endMs, text}."""
    cues = []
    for event in events:
        segs = event.get("segs", [])
        text = "".join(s.get("utf8", "") for s in segs).replace("\n", " ").strip()
        if not text:
            continue
        start_ms = event.get("tStartMs", 0)
        dur_ms = event.get("dDurationMs", 2000)
        cues.append({"startMs": start_ms, "endMs": start_ms + dur_ms, "text": text})
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


async def _fetch_and_cache_one(video: dict) -> bool:
    """
    Try to fetch subtitles for one video and store in the prepared-video caches.
    Returns True if cached successfully, False if blocked/failed.
    """
    video_id = video["videoId"]
    lock = _get_video_lock(video_id)
    async with lock:
        if await _load_session_from_fast_cache(video_id):
            return True

        await _mark_video_status(video, "processing")

        try:
            loop = asyncio.get_event_loop()
            cues, selected_lang, all_langs = await loop.run_in_executor(
                None, _fetch_subtitles_ytdlp, video_id
            )
        except Exception as exc:
            logger.warning("Cache warmer fetch failed for %s: %s", video_id, exc)
            await _mark_video_status(video, "failed", str(exc))
            return False

        if not cues:
            await _mark_video_status(video, "failed", "empty subtitle cues")
            return False

        result = {
            "videoId": video_id,
            "title": video.get("title", video_id),
            "cues": cues,
            "selectedLanguage": selected_lang,
            "availableLanguages": all_langs,
        }

        await _store_prepared_session(result, video)
        return True


async def warm_subtitle_cache(
    *,
    limit: int = _FIXED_LIBRARY_SIZE,
    delay_seconds: int = _WARM_DELAY,
) -> None:
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
        videos = await get_fixed_library_videos(limit=_FIXED_LIBRARY_SIZE)
        videos = videos[: max(1, min(limit, _FIXED_LIBRARY_SIZE))]
        cached_count = 0
        fetched_count = 0

        for video in videos:
            vid = video["videoId"]
            if await _load_session_from_fast_cache(vid):
                cached_count += 1
                continue

            # Not prepared yet — fetch slowly in the background.
            if fetched_count > 0 and delay_seconds > 0:
                await asyncio.sleep(delay_seconds)

            ok = await _fetch_and_cache_one(video)
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


def schedule_subtitle_cache_warm() -> None:
    """Start a background warmup if one is not already running."""
    global _warm_task
    if _warm_task and not _warm_task.done():
        return

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return

    _warm_task = loop.create_task(warm_subtitle_cache())


async def get_cached_video_ids() -> set[str]:
    """Return set of video IDs that already have prepared subtitles."""
    result: set[str] = set()
    try:
        videos = await get_fixed_library_videos(limit=_FIXED_LIBRARY_SIZE)
        for video in videos:
            vid = video["videoId"]
            if await _load_session_from_fast_cache(vid):
                result.add(vid)

        if mongo_service.is_ready():
            cursor = mongo_service.db().subtitle_video_sessions.find(
                {
                    "status": "ready",
                    "videoId": {"$in": [video["videoId"] for video in videos]},
                },
                {"videoId": 1},
            )
            async for doc in cursor:
                if doc.get("videoId"):
                    result.add(doc["videoId"])
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


def _published_at_from_ytdlp(entry: dict) -> str:
    upload_date = entry.get("upload_date")
    if upload_date and re.fullmatch(r"\d{8}", str(upload_date)):
        upload_date = str(upload_date)
        return f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:8]}T00:00:00Z"

    timestamp = entry.get("timestamp") or entry.get("release_timestamp")
    if timestamp:
        try:
            return datetime.fromtimestamp(int(timestamp), tz=timezone.utc).isoformat()
        except Exception:
            return ""

    return ""


def _thumbnail_from_ytdlp(entry: dict) -> str:
    if entry.get("thumbnail"):
        return entry["thumbnail"]

    thumbnails = entry.get("thumbnails") or []
    for thumbnail in reversed(thumbnails):
        if thumbnail.get("url"):
            return thumbnail["url"]
    return ""


def _video_from_ytdlp_entry(entry: dict) -> dict | None:
    video_id = entry.get("id") or entry.get("url")
    if not video_id or not re.fullmatch(r"[\w-]{11}", str(video_id)):
        return None

    return {
        "videoId": str(video_id),
        "title": entry.get("title") or str(video_id),
        "publishedAt": _published_at_from_ytdlp(entry),
        "thumbnailUrl": _thumbnail_from_ytdlp(entry),
        "videoUrl": f"https://www.youtube.com/watch?v={video_id}",
    }


def _merge_channel_videos(*sources: list[dict], limit: int) -> list[dict]:
    merged: list[dict] = []
    seen: set[str] = set()

    for source in sources:
        for video in source:
            video_id = video.get("videoId")
            if not video_id or video_id in seen:
                continue
            merged.append(video)
            seen.add(video_id)
            if len(merged) >= limit:
                return merged

    return merged


async def _fetch_channel_feed_videos(limit: int) -> list[dict]:
    async with aiohttp.ClientSession() as session:
        async with session.get(_CHANNEL_FEED_URL, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            if resp.status != 200:
                raise RuntimeError("Не вдалося завантажити список відео каналу.")
            xml_text = await resp.text()

    return _parse_channel_feed(xml_text, limit)


def _fetch_channel_videos_ytdlp(limit: int) -> list[dict]:
    import yt_dlp  # noqa: PLC0415

    ydl_opts = {
        "extract_flat": "in_playlist",
        "ignore_no_formats_error": True,
        "playlistend": limit,
        "quiet": True,
        "skip_download": True,
        "no_warnings": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(_CHANNEL_VIDEOS_URL, download=False)

    videos: list[dict] = []
    for entry in info.get("entries") or []:
        video = _video_from_ytdlp_entry(entry)
        if video:
            videos.append(video)
            if len(videos) >= limit:
                break
    return videos


async def _fetch_channel_videos(limit: int) -> list[dict]:
    rss_videos: list[dict] = []
    try:
        rss_videos = await _fetch_channel_feed_videos(limit)
    except Exception as exc:
        logger.warning("YouTube RSS video list failed: %s", exc)

    if len(rss_videos) >= limit:
        return rss_videos[:limit]

    try:
        loop = asyncio.get_event_loop()
        ytdlp_videos = await loop.run_in_executor(
            None,
            _fetch_channel_videos_ytdlp,
            limit,
        )
    except Exception as exc:
        logger.warning("yt-dlp channel video list failed: %s", exc)
        ytdlp_videos = []

    videos = _merge_channel_videos(rss_videos, ytdlp_videos, limit=limit)
    if not videos:
        raise RuntimeError("Канал не повернув жодного відео.")
    return videos


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _public_session_fields(document: dict) -> dict:
    return {
        "videoId": document["videoId"],
        "title": document.get("title") or document["videoId"],
        "cues": document.get("cues", []),
        "selectedLanguage": document.get("selectedLanguage", ""),
        "availableLanguages": document.get("availableLanguages", []),
    }


def _video_card_from_session_doc(document: dict) -> dict:
    return {
        "videoId": document["videoId"],
        "title": document.get("title") or document["videoId"],
        "publishedAt": document.get("publishedAt", ""),
        "thumbnailUrl": document.get("thumbnailUrl", ""),
        "videoUrl": document.get("videoUrl") or f"https://www.youtube.com/watch?v={document['videoId']}",
        "cached": True,
    }


async def _load_session_from_mongo(video_id: str) -> dict | None:
    if not mongo_service.is_ready():
        return None

    document = await mongo_service.db().subtitle_video_sessions.find_one(
        {"videoId": video_id, "status": "ready"}
    )
    if not document:
        return None

    result = _public_session_fields(document)
    if not result["cues"]:
        return None
    return result


async def _store_prepared_session(result: dict, video_meta: dict | None = None) -> None:
    video_id = result["videoId"]
    _session_cache[video_id] = (result, time.time())

    try:
        if redis_service.redis:
            await redis_service.set(
                f"subtitle:session:{video_id}",
                json.dumps(result),
                ex=_REDIS_SUBTITLE_TTL,
            )
    except Exception as exc:
        logger.debug("Redis subtitle cache write failed: %s", exc)

    if not mongo_service.is_ready():
        return

    video_meta = video_meta or {}
    now = _now_utc()
    update_doc = {
        "videoId": video_id,
        "title": result.get("title") or video_meta.get("title") or video_id,
        "cues": result.get("cues", []),
        "selectedLanguage": result.get("selectedLanguage", ""),
        "availableLanguages": result.get("availableLanguages", []),
        "status": "ready",
        "fetchedAt": now,
        "updatedAt": now,
        "lastError": "",
    }
    for key in ("publishedAt", "thumbnailUrl", "videoUrl"):
        if video_meta.get(key):
            update_doc[key] = video_meta[key]

    await mongo_service.db().subtitle_video_sessions.update_one(
        {"videoId": video_id},
        {"$set": update_doc, "$setOnInsert": {"createdAt": now}},
        upsert=True,
    )


async def _mark_video_status(video: dict, status: str, error: str = "") -> None:
    if not mongo_service.is_ready():
        return

    now = _now_utc()
    update_doc = {
        "videoId": video["videoId"],
        "title": video.get("title") or video["videoId"],
        "publishedAt": video.get("publishedAt", ""),
        "thumbnailUrl": video.get("thumbnailUrl", ""),
        "videoUrl": video.get("videoUrl") or f"https://www.youtube.com/watch?v={video['videoId']}",
        "status": status,
        "lastAttemptAt": now,
        "updatedAt": now,
        "lastError": error,
    }
    await mongo_service.db().subtitle_video_sessions.update_one(
        {"videoId": video["videoId"]},
        {"$set": update_doc, "$setOnInsert": {"createdAt": now}},
        upsert=True,
    )


async def _load_session_from_fast_cache(video_id: str) -> dict | None:
    cached = _session_cache.get(video_id)
    if cached:
        result, ts = cached
        if time.time() - ts < _CACHE_TTL and result.get("cues"):
            return result
        del _session_cache[video_id]

    try:
        if redis_service.redis:
            cached_json = await redis_service.get(f"subtitle:session:{video_id}")
            if cached_json:
                result = json.loads(cached_json)
                if result.get("cues"):
                    _session_cache[video_id] = (result, time.time())
                    return result
    except Exception as exc:
        logger.debug("Redis subtitle cache read failed: %s", exc)

    result = await _load_session_from_mongo(video_id)
    if result:
        _session_cache[video_id] = (result, time.time())
        try:
            if redis_service.redis:
                await redis_service.set(
                    f"subtitle:session:{video_id}",
                    json.dumps(result),
                    ex=_REDIS_SUBTITLE_TTL,
                )
        except Exception as exc:
            logger.debug("Redis subtitle cache backfill failed: %s", exc)

    return result


def _cache_fixed_library(videos: list[dict]) -> None:
    global _fixed_library_cache
    _fixed_library_cache = videos[:_FIXED_LIBRARY_SIZE]


async def _load_fixed_library_from_redis() -> list[dict] | None:
    try:
        if redis_service.redis:
            cached_json = await redis_service.get(_REDIS_FIXED_LIBRARY_KEY)
            if cached_json:
                videos = json.loads(cached_json)
                if len(videos) >= _FIXED_LIBRARY_SIZE:
                    return videos[:_FIXED_LIBRARY_SIZE]
    except Exception as exc:
        logger.debug("Redis fixed video library read failed: %s", exc)
    return None


async def _store_fixed_library_in_redis(videos: list[dict]) -> None:
    try:
        if redis_service.redis:
            await redis_service.set(
                _REDIS_FIXED_LIBRARY_KEY,
                json.dumps(videos[:_FIXED_LIBRARY_SIZE]),
                ex=_REDIS_FIXED_LIBRARY_TTL,
            )
    except Exception as exc:
        logger.debug("Redis fixed video library write failed: %s", exc)


async def _load_fixed_library_from_mongo() -> list[dict] | None:
    if not mongo_service.is_ready():
        return None

    document = await mongo_service.db().subtitle_video_catalogs.find_one(
        {"_id": _FIXED_LIBRARY_DOC_ID}
    )
    if not document:
        return None

    videos = document.get("videos") or []
    if len(videos) < _FIXED_LIBRARY_SIZE:
        return None
    return videos[:_FIXED_LIBRARY_SIZE]


async def _store_fixed_library_in_mongo(seed_videos: list[dict]) -> list[dict]:
    if not mongo_service.is_ready():
        return seed_videos[:_FIXED_LIBRARY_SIZE]

    collection = mongo_service.db().subtitle_video_catalogs
    existing = await collection.find_one({"_id": _FIXED_LIBRARY_DOC_ID})
    now = _now_utc()

    if existing:
        existing_videos = existing.get("videos") or []
        if len(existing_videos) >= _FIXED_LIBRARY_SIZE:
            return existing_videos[:_FIXED_LIBRARY_SIZE]

        seen = {video.get("videoId") for video in existing_videos}
        merged = list(existing_videos)
        for video in seed_videos:
            if video.get("videoId") not in seen:
                merged.append(video)
                seen.add(video.get("videoId"))
            if len(merged) >= _FIXED_LIBRARY_SIZE:
                break

        await collection.update_one(
            {"_id": _FIXED_LIBRARY_DOC_ID},
            {
                "$set": {
                    "videos": merged[:_FIXED_LIBRARY_SIZE],
                    "size": len(merged[:_FIXED_LIBRARY_SIZE]),
                    "updatedAt": now,
                }
            },
        )
        return merged[:_FIXED_LIBRARY_SIZE]

    library_videos = seed_videos[:_FIXED_LIBRARY_SIZE]
    await collection.update_one(
        {"_id": _FIXED_LIBRARY_DOC_ID},
        {
            "$setOnInsert": {
                "_id": _FIXED_LIBRARY_DOC_ID,
                "channel": "KurzgesagtDE",
                "sourceUrl": _CHANNEL_VIDEOS_URL,
                "videos": library_videos,
                "size": len(library_videos),
                "lockedAt": now,
                "createdAt": now,
                "updatedAt": now,
            }
        },
        upsert=True,
    )

    document = await collection.find_one({"_id": _FIXED_LIBRARY_DOC_ID})
    return (document or {}).get("videos", library_videos)[:_FIXED_LIBRARY_SIZE]


async def get_fixed_library_videos(limit: int = _FIXED_LIBRARY_SIZE) -> list[dict]:
    """Return the pinned Kurzgesagt DE trainer catalog."""
    if _fixed_library_cache and len(_fixed_library_cache) >= _FIXED_LIBRARY_SIZE:
        return _fixed_library_cache[:limit]

    mongo_videos = await _load_fixed_library_from_mongo()
    if mongo_videos:
        _cache_fixed_library(mongo_videos)
        await _store_fixed_library_in_redis(mongo_videos)
        return mongo_videos[:limit]

    redis_videos = await _load_fixed_library_from_redis()
    if redis_videos:
        if mongo_service.is_ready():
            redis_videos = await _store_fixed_library_in_mongo(redis_videos)
        _cache_fixed_library(redis_videos)
        return redis_videos[:limit]

    seed_videos = await _fetch_channel_videos(_FIXED_LIBRARY_SIZE)
    if len(seed_videos) < _FIXED_LIBRARY_SIZE:
        raise RuntimeError("Не вдалося отримати 20 відео Kurzgesagt DE.")

    library_videos = await _store_fixed_library_in_mongo(seed_videos)
    _cache_fixed_library(library_videos)
    await _store_fixed_library_in_redis(library_videos)
    return library_videos[:limit]


async def _get_ready_video_ids(video_ids: list[str]) -> set[str]:
    ready: set[str] = set()
    missing: list[str] = []

    for video_id in video_ids:
        cached = _session_cache.get(video_id)
        if cached:
            result, ts = cached
            if time.time() - ts < _CACHE_TTL and result.get("cues"):
                ready.add(video_id)
                continue
            _session_cache.pop(video_id, None)
        missing.append(video_id)

    if missing:
        try:
            if redis_service.redis:
                keys = [f"subtitle:session:{video_id}" for video_id in missing]
                values = await redis_service.redis.mget(keys)
                still_missing: list[str] = []
                for video_id, cached_json in zip(missing, values):
                    if not cached_json:
                        still_missing.append(video_id)
                        continue
                    result = json.loads(cached_json)
                    if result.get("cues"):
                        _session_cache[video_id] = (result, time.time())
                        ready.add(video_id)
                    else:
                        still_missing.append(video_id)
                missing = still_missing
        except Exception as exc:
            logger.debug("Redis ready-video batch read failed: %s", exc)

    if missing and mongo_service.is_ready():
        cursor = mongo_service.db().subtitle_video_sessions.find(
            {
                "videoId": {"$in": missing},
                "status": "ready",
                "cues.0": {"$exists": True},
            },
            {"videoId": 1},
        )
        async for document in cursor:
            if document.get("videoId"):
                ready.add(document["videoId"])

    return ready


async def _collect_prepared_video_cards(channel_videos: list[dict], limit: int) -> list[dict]:
    items: list[dict] = []
    ready_ids = await _get_ready_video_ids([video["videoId"] for video in channel_videos])

    for video in channel_videos:
        if video["videoId"] in ready_ids:
            prepared = dict(video)
            prepared["cached"] = True
            items.append(prepared)
            if len(items) >= limit:
                return items

    return items


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def list_channel_videos(limit: int = _FIXED_LIBRARY_SIZE) -> list[dict]:
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
                if len(videos) >= limit:
                    _channel_videos_cache = (videos, time.time())
                    logger.info("Channel videos loaded from Redis cache")
                    return videos[:limit]
    except Exception as exc:
        logger.debug("Redis channel cache read failed: %s", exc)

    videos = await _fetch_channel_videos(max(limit, _FIXED_LIBRARY_SIZE))

    # Store in both caches
    _channel_videos_cache = (videos, time.time())
    try:
        if redis_service.redis:
            await redis_service.set("subtitle:channel_videos", json.dumps(videos), ex=_REDIS_CHANNEL_TTL)
    except Exception as exc:
        logger.debug("Redis channel cache write failed: %s", exc)

    return videos[:limit]


async def ensure_prepared_library(
    *,
    min_ready: int = _MIN_READY_LIBRARY_SIZE,
    limit: int = _FIXED_LIBRARY_SIZE,
) -> list[dict]:
    """
    Ensure the learner-facing catalog has a minimum number of ready videos.

    This is the bootstrap path: it may perform YouTube work, but only before
    the catalog response is sent or from startup jobs. Video clicks still read
    already prepared sessions only.
    """
    limit = max(1, min(limit, _FIXED_LIBRARY_SIZE))
    min_ready = max(1, min(min_ready, limit))
    library_videos = await get_fixed_library_videos(limit=_FIXED_LIBRARY_SIZE)
    items = await _collect_prepared_video_cards(library_videos, limit)
    if len(items) >= min_ready:
        return items

    ready_ids = {item["videoId"] for item in items}
    for video in library_videos:
        if len(items) >= min_ready:
            break
        if video["videoId"] in ready_ids:
            continue

        ok = await _fetch_and_cache_one(video)
        if not ok:
            continue

        prepared = dict(video)
        prepared["cached"] = True
        items.append(prepared)
        ready_ids.add(video["videoId"])

    return items[:limit]


async def _bootstrap_prepared_library() -> None:
    try:
        await ensure_prepared_library()
    except Exception as exc:
        logger.warning("Prepared fixed video library bootstrap failed: %s", exc)


def schedule_prepared_library_bootstrap() -> None:
    """Prepare the first catalog page in the background after app startup."""
    global _bootstrap_task
    if _bootstrap_task and not _bootstrap_task.done():
        return

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return

    _bootstrap_task = loop.create_task(_bootstrap_prepared_library())


async def list_prepared_videos(
    limit: int = _FIXED_LIBRARY_SIZE,
    *,
    ensure_min_ready: int = 0,
) -> list[dict]:
    """
    Return only videos whose subtitle sessions are already prepared.

    The catalog is a fixed 20-video Kurzgesagt DE library. This endpoint does
    not do slow YouTube subtitle work; it only returns sessions already stored
    in MongoDB/Redis and starts a background bootstrap when something is missing.
    """
    try:
        library_videos = await get_fixed_library_videos(limit=_FIXED_LIBRARY_SIZE)
    except Exception as exc:
        logger.warning("Fixed video library load failed: %s", exc)
        library_videos = []

    limit = max(1, min(limit, _FIXED_LIBRARY_SIZE))
    items = await _collect_prepared_video_cards(library_videos, limit)
    if len(items) < ensure_min_ready:
        schedule_prepared_library_bootstrap()

    schedule_subtitle_cache_warm()
    return items


async def get_prepared_video_session(input_str: str) -> dict:
    """Return a prepared subtitle session without doing live YouTube work."""
    video_id = _extract_video_id(input_str)
    if not video_id:
        raise ValueError("Не вдалося розпізнати YouTube URL або ID відео.")

    library_videos = await get_fixed_library_videos(limit=_FIXED_LIBRARY_SIZE)
    if video_id not in {video["videoId"] for video in library_videos}:
        raise ValueError("Це відео не входить у фіксовану бібліотеку Kurzgesagt DE.")

    result = await _load_session_from_fast_cache(video_id)
    if result:
        return result

    schedule_subtitle_cache_warm()
    raise RuntimeError("Це відео ще не підготовлене. Спробуйте інше готове відео.")


async def load_video_session(input_str: str, preferred_title: Optional[str] = None) -> dict:
    """
    Download and persist subtitle metadata for a YouTube video.

    Strategy:
      1. Return a prepared session from memory/Redis/MongoDB.
      2. If missing, fetch via yt-dlp.
      3. Store the prepared result in MongoDB + Redis before returning.

    Returns:
        {videoId, title, cues, selectedLanguage, availableLanguages}
    """
    video_id = _extract_video_id(input_str)
    if not video_id:
        raise ValueError("Не вдалося розпізнати YouTube URL або ID відео.")

    prepared = await _load_session_from_fast_cache(video_id)
    if prepared:
        logger.info("Prepared subtitle cache hit for %s", video_id)
        return prepared

    # --- Lock per video: thundering herd protection ---
    # If 60 users click the same video, only 1 goes to YouTube.
    # The other 59 wait here and get the result from cache.
    lock = _get_video_lock(video_id)
    async with lock:
        prepared = await _load_session_from_fast_cache(video_id)
        if prepared:
            logger.info("Prepared subtitle cache hit (post-lock) for %s", video_id)
            return prepared

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

        await _store_prepared_session(
            result,
            {
                "videoId": video_id,
                "title": title,
                "videoUrl": f"https://www.youtube.com/watch?v={video_id}",
            },
        )

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
