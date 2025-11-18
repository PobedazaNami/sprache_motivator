"""
MongoDB service using Motor (async driver).
This service is optional and initializes only if MONGODB_URI is provided.
"""
from __future__ import annotations

from typing import Optional, Tuple, List, Dict
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
    default_db = _client.get_default_database()
    db_name = default_db.name if default_db is not None else "sprache_motivator"
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


def _today_midnight_utc() -> datetime:
    return datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)


async def update_daily_stats(
    user_id: int,
    quality_percentage: int,
    expected_total: Optional[int] = None,
    is_correct: Optional[bool] = None,
) -> None:
    """Increment today's counters and keep aggregates for quality/penalties."""
    if not is_ready():
        return

    today = _today_midnight_utc()
    quality_value = max(0, int(quality_percentage or 0))
    now = datetime.now(timezone.utc)

    inc_doc = {
        "total_tasks": 1,
        "completed_tasks": 1,
        "quality_sum": quality_value,
    }
    if is_correct is True:
        inc_doc["correct_answers"] = 1
    elif is_correct is False:
        inc_doc["incorrect_answers"] = 1

    set_on_insert_doc = {
        "created_at": now,
    }
    if expected_total is None:
        # Default expected task count for new day when user hasn't configured goals.
        set_on_insert_doc["expected_tasks"] = 0

    update_doc = {
        "$inc": inc_doc,
        "$set": {
            "updated_at": now,
            "last_answer_quality": quality_value,
            "last_answer_at": now,
        },
        "$setOnInsert": set_on_insert_doc,
    }

    if expected_total is not None:
        update_doc.setdefault("$max", {})["expected_tasks"] = max(0, expected_total)

    await db().daily_stats.update_one(
        {"user_id": user_id, "date": today},
        update_doc,
        upsert=True,
    )


async def get_today_stats(user_id: int) -> Optional[dict]:
    if not is_ready():
        return None
    today = _today_midnight_utc()
    doc = await db().daily_stats.find_one({"user_id": user_id, "date": today})
    if not doc:
        return None
    completed = int(doc.get("completed_tasks", 0))
    average_quality = int((doc.get("quality_sum", 0) / max(1, completed))) if completed else 0
    expected = int(doc.get("expected_tasks", 0))
    return {
        "completed": completed,
        "total": int(doc.get("total_tasks", 0)),
        "quality": average_quality,
        "expected": expected,
        "correct": int(doc.get("correct_answers", 0)),
        "incorrect": int(doc.get("incorrect_answers", 0)),
    }


async def get_today_stats_bulk(user_ids: List[int]) -> Dict[int, dict]:
    if not is_ready() or not user_ids:
        return {}
    today = _today_midnight_utc()
    cursor = db().daily_stats.find({
        "user_id": {"$in": user_ids},
        "date": today,
    })
    results: Dict[int, dict] = {}
    async for doc in cursor:
        user_id = int(doc.get("user_id"))
        completed = int(doc.get("completed_tasks", 0))
        average_quality = int((doc.get("quality_sum", 0) / max(1, completed))) if completed else 0
        results[user_id] = {
            "completed": completed,
            "total": int(doc.get("total_tasks", 0)),
            "quality": average_quality,
            "expected": int(doc.get("expected_tasks", 0)),
            "correct": int(doc.get("correct_answers", 0)),
            "incorrect": int(doc.get("incorrect_answers", 0)),
        }
    return results


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


# ---------------------------------------------------------------------------
# Friend/Group Management
# ---------------------------------------------------------------------------

async def add_friend(user_id: int, friend_id: int) -> bool:
    """Add a friend relationship. Returns True if successfully added."""
    if not is_ready():
        return False
    
    # Create bidirectional friendship
    now = datetime.now(timezone.utc)
    
    # Check if friendship already exists
    existing = await db().friendships.find_one({
        "$or": [
            {"user_id": user_id, "friend_id": friend_id},
            {"user_id": friend_id, "friend_id": user_id}
        ]
    })
    
    if existing:
        return False  # Already friends
    
    # Add friendship (store both directions for easier queries)
    await db().friendships.insert_one({
        "user_id": user_id,
        "friend_id": friend_id,
        "created_at": now,
    })
    
    return True


async def remove_friend(user_id: int, friend_id: int) -> bool:
    """Remove a friend relationship. Returns True if successfully removed."""
    if not is_ready():
        return False
    
    # Remove bidirectional friendship
    result = await db().friendships.delete_many({
        "$or": [
            {"user_id": user_id, "friend_id": friend_id},
            {"user_id": friend_id, "friend_id": user_id}
        ]
    })
    
    return result.deleted_count > 0


async def get_friends(user_id: int) -> List[int]:
    """Get list of friend IDs for a user."""
    if not is_ready():
        return []
    
    # Find all friendships where user is either user_id or friend_id
    cursor = db().friendships.find({
        "$or": [
            {"user_id": user_id},
            {"friend_id": user_id}
        ]
    })
    
    friend_ids = []
    async for doc in cursor:
        # Add the other user's ID
        if doc.get("user_id") == user_id:
            friend_ids.append(int(doc.get("friend_id")))
        else:
            friend_ids.append(int(doc.get("user_id")))
    
    return friend_ids


async def get_friends_stats(user_id: int) -> Dict[int, dict]:
    """Get today's stats for all friends of a user."""
    if not is_ready():
        return {}
    
    friend_ids = await get_friends(user_id)
    if not friend_ids:
        return {}
    
    return await get_today_stats_bulk(friend_ids)
