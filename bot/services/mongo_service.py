"""
MongoDB service using Motor (async driver).
This service is optional and initializes only if MONGODB_URI is provided.
"""
from __future__ import annotations

from typing import Optional, Tuple
from datetime import datetime, timezone, timedelta

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from bot.config import settings

_client: Optional[AsyncIOMotorClient] = None
_db: Optional[AsyncIOMotorDatabase] = None


async def init() -> bool:
    """Initialize Mongo client if URI provided. Returns True if initialized."""
    global _client, _db
    if not settings.MONGODB_URI:
        return False
    _client = AsyncIOMotorClient(settings.MONGODB_URI)
    # If no database name specified in URI, use default 'sprache_motivator'
    db_name = _client.get_default_database().name if _client.get_default_database() else "sprache_motivator"
    _db = _client[db_name]
    # Create indexes (idempotent)
    await _db.daily_stats.create_index([("user_id", 1), ("date", 1)], unique=True)
    await _db.training_sessions.create_index([("user_id", 1), ("created_at", 1)])
    return True


def is_ready() -> bool:
    return _db is not None


def db() -> AsyncIOMotorDatabase:
    assert _db is not None, "Mongo DB is not initialized"
    return _db


async def store_training_session(user_id: int, sentence: str, expected: str, difficulty: str) -> str:
    """Store a training session (lightweight duplicate of SQL storage). Returns inserted id as string."""
    if not is_ready():
        return ""
    doc = {
        "user_id": user_id,
        "sentence": sentence,
        "expected_translation": expected,
        "difficulty_level": difficulty,
        "created_at": datetime.now(timezone.utc),
    }
    res = await db().training_sessions.insert_one(doc)
    return str(res.inserted_id)


async def update_daily_stats(user_id: int, quality_percentage: int) -> None:
    """Increment today's counters and recompute average quality."""
    if not is_ready():
        return
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    # Upsert with atomic operators
    await db().daily_stats.update_one(
        {"user_id": user_id, "date": today},
        {
            "$inc": {"total_tasks": 1, "completed_tasks": 1, "quality_sum": quality_percentage},
            "$setOnInsert": {"created_at": datetime.now(timezone.utc)}
        },
        upsert=True
    )


async def get_today_stats(user_id: int) -> Optional[dict]:
    if not is_ready():
        return None
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    doc = await db().daily_stats.find_one({"user_id": user_id, "date": today})
    if not doc:
        return None
    average_quality = int((doc.get("quality_sum", 0) / max(1, doc.get("completed_tasks", 0))))
    return {
        "completed": int(doc.get("completed_tasks", 0)),
        "total": int(doc.get("total_tasks", 0)),
        "quality": average_quality,
    }


async def get_week_stats(user_id: int) -> Optional[Tuple[int, int, int]]:
    if not is_ready():
        return None
    today = datetime.now(timezone.utc)
    week_start = today - timedelta(days=today.weekday())
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
    pipeline = [
        {"$match": {"user_id": user_id, "date": {"$gte": week_start}}},
        {"$group": {
            "_id": None,
            "completed": {"$sum": "$completed_tasks"},
            "total": {"$sum": "$total_tasks"},
            "quality_sum": {"$sum": "$quality_sum"}
        }}
    ]
    agg = await db().daily_stats.aggregate(pipeline).to_list(length=1)
    if not agg:
        return None
    a = agg[0]
    completed = int(a.get("completed", 0))
    total = int(a.get("total", 0))
    avg_quality = int((a.get("quality_sum", 0) / max(1, completed)))
    return completed, total, avg_quality
