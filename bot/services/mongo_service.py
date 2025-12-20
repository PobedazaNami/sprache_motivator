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
    # Index for mastered sentences (sentences translated with 100% quality)
    await _db.mastered_sentences.create_index([("user_id", 1), ("sentence_hash", 1)], unique=True)
    await _db.mastered_sentences.create_index([("user_id", 1), ("topic", 1)])
    # Index for user streaks (motivation system)
    await _db.user_streaks.create_index([("user_id", 1)], unique=True)
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

async def send_friend_request(user_id: int, friend_id: int) -> bool:
    """Send a friend request. Returns True if successfully sent."""
    if not is_ready():
        return False
    
    now = datetime.now(timezone.utc)
    
    # Check if active friendship or pending request already exists
    # Only check for "pending" and "accepted" statuses
    existing = await db().friendships.find_one({
        "$and": [
            {
                "$or": [
                    {"user_id": user_id, "friend_id": friend_id},
                    {"user_id": friend_id, "friend_id": user_id}
                ]
            },
            {
                "status": {"$in": ["pending", "accepted"]}
            }
        ]
    })
    
    if existing:
        return False  # Already friends or request exists
    
    # Create friend request (pending status)
    await db().friendships.insert_one({
        "user_id": user_id,
        "friend_id": friend_id,
        "status": "pending",
        "created_at": now,
    })
    
    return True


async def accept_friend_request(user_id: int, requester_id: int) -> bool:
    """Accept a friend request. Returns True if successfully accepted."""
    if not is_ready():
        return False
    
    now = datetime.now(timezone.utc)
    
    # Find the pending request where requester sent to user
    result = await db().friendships.update_one(
        {
            "user_id": requester_id,
            "friend_id": user_id,
            "status": "pending"
        },
        {
            "$set": {
                "status": "accepted",
                "accepted_at": now,
            }
        }
    )
    
    return result.modified_count > 0


async def reject_friend_request(user_id: int, requester_id: int) -> bool:
    """Reject a friend request. Returns True if successfully rejected."""
    if not is_ready():
        return False
    
    # Delete the pending request
    result = await db().friendships.delete_one({
        "user_id": requester_id,
        "friend_id": user_id,
        "status": "pending"
    })
    
    return result.deleted_count > 0


async def get_pending_incoming_requests(user_id: int) -> List[int]:
    """Get list of user IDs who sent pending friend requests to this user."""
    if not is_ready():
        return []
    
    cursor = db().friendships.find({
        "friend_id": user_id,
        "status": "pending"
    })
    
    requester_ids = []
    async for doc in cursor:
        requester_ids.append(int(doc.get("user_id")))
    
    return requester_ids


async def get_pending_outgoing_requests(user_id: int) -> List[int]:
    """Get list of user IDs to whom this user sent pending friend requests."""
    if not is_ready():
        return []
    
    cursor = db().friendships.find({
        "user_id": user_id,
        "status": "pending"
    })
    
    friend_ids = []
    async for doc in cursor:
        friend_ids.append(int(doc.get("friend_id")))
    
    return friend_ids


async def add_friend(user_id: int, friend_id: int) -> bool:
    """Legacy function for backward compatibility. Use send_friend_request instead."""
    return await send_friend_request(user_id, friend_id)


async def remove_friend(user_id: int, friend_id: int) -> bool:
    """Remove a friend relationship (accepted friendships only). Returns True if successfully removed."""
    if not is_ready():
        return False
    
    # Remove accepted friendship (bidirectional)
    result = await db().friendships.delete_many({
        "$or": [
            {"user_id": user_id, "friend_id": friend_id, "status": "accepted"},
            {"user_id": friend_id, "friend_id": user_id, "status": "accepted"}
        ]
    })
    
    return result.deleted_count > 0


async def get_friends(user_id: int) -> List[int]:
    """Get list of accepted friend IDs for a user."""
    if not is_ready():
        return []
    
    # Find all accepted friendships where user is either user_id or friend_id
    cursor = db().friendships.find({
        "$or": [
            {"user_id": user_id, "status": "accepted"},
            {"friend_id": user_id, "status": "accepted"}
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


# ---------------------------------------------------------------------------
# Mastered Sentences Management
# ---------------------------------------------------------------------------

def _hash_sentence(sentence: str) -> str:
    """Create a normalized hash of a sentence for comparison."""
    import hashlib
    # Normalize: lowercase, strip whitespace, remove extra spaces
    normalized = ' '.join(sentence.lower().strip().split())
    return hashlib.md5(normalized.encode('utf-8')).hexdigest()


async def add_mastered_sentence(
    user_id: int,
    sentence: str,
    translation: str,
    topic: Optional[str] = None,
    difficulty: Optional[str] = None
) -> bool:
    """Add a sentence that user translated with 100% quality.
    Returns True if added, False if already exists or error."""
    if not is_ready():
        return False
    
    sentence_hash = _hash_sentence(sentence)
    now = datetime.now(timezone.utc)
    
    try:
        await db().mastered_sentences.insert_one({
            "user_id": user_id,
            "sentence_hash": sentence_hash,
            "sentence": sentence,
            "translation": translation,
            "topic": topic,
            "difficulty": difficulty,
            "mastered_at": now,
        })
        return True
    except Exception:
        # Duplicate key error means already mastered
        return False


async def is_sentence_mastered(user_id: int, sentence: str) -> bool:
    """Check if user has already mastered this sentence (100% quality)."""
    if not is_ready():
        return False
    
    sentence_hash = _hash_sentence(sentence)
    doc = await db().mastered_sentences.find_one({
        "user_id": user_id,
        "sentence_hash": sentence_hash
    })
    return doc is not None


async def get_mastered_sentences_hashes(user_id: int, topic: Optional[str] = None, limit: int = 1000) -> List[str]:
    """Get list of sentence hashes that user has mastered.
    Optionally filter by topic. Returns up to `limit` hashes."""
    if not is_ready():
        return []
    
    query = {"user_id": user_id}
    if topic:
        query["topic"] = topic
    
    cursor = db().mastered_sentences.find(query, {"sentence_hash": 1}).limit(limit)
    hashes = []
    async for doc in cursor:
        hashes.append(doc.get("sentence_hash"))
    return hashes


async def get_mastered_count(user_id: int, topic: Optional[str] = None) -> int:
    """Get count of mastered sentences for a user, optionally filtered by topic."""
    if not is_ready():
        return 0
    
    query = {"user_id": user_id}
    if topic:
        query["topic"] = topic
    
    return await db().mastered_sentences.count_documents(query)


# ---------------------------------------------------------------------------
# Streak Management (Motivation System)
# ---------------------------------------------------------------------------

async def update_streak(user_id: int) -> Tuple[int, bool, Optional[int]]:
    """
    Update user's learning streak when they complete at least one task.
    Returns: (current_streak_days, is_new_milestone, milestone_reached)
    Milestones: 3, 7, 14, 30, 60, 100 days
    """
    if not is_ready():
        return 0, False, None
    
    now = datetime.now(timezone.utc)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday = today - timedelta(days=1)
    
    # Get current streak data
    streak_doc = await db().user_streaks.find_one({"user_id": user_id})
    
    milestones = [3, 7, 14, 30, 60, 100]
    
    if not streak_doc:
        # First day ever - create streak
        await db().user_streaks.insert_one({
            "user_id": user_id,
            "current_streak": 1,
            "longest_streak": 1,
            "last_activity_date": today,
            "milestones_achieved": [],
            "created_at": now,
        })
        return 1, False, None
    
    last_activity = streak_doc.get("last_activity_date")
    current_streak = streak_doc.get("current_streak", 0)
    longest_streak = streak_doc.get("longest_streak", 0)
    milestones_achieved = streak_doc.get("milestones_achieved", [])
    
    # Normalize last_activity to UTC if it's offset-naive
    if last_activity and last_activity.tzinfo is None:
        last_activity = last_activity.replace(tzinfo=timezone.utc)
    
    # Already updated today
    if last_activity and last_activity >= today:
        return current_streak, False, None
    
    # Check if streak continues or breaks
    if last_activity and last_activity >= yesterday:
        # Streak continues!
        new_streak = current_streak + 1
    else:
        # Streak broken - start over
        new_streak = 1
    
    # Check for new milestone
    new_milestone = None
    is_new_milestone = False
    for m in milestones:
        if new_streak >= m and m not in milestones_achieved:
            new_milestone = m
            milestones_achieved.append(m)
            is_new_milestone = True
            break  # Only one milestone at a time
    
    # Update database
    await db().user_streaks.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "current_streak": new_streak,
                "longest_streak": max(longest_streak, new_streak),
                "last_activity_date": today,
                "milestones_achieved": milestones_achieved,
                "updated_at": now,
            }
        }
    )
    
    return new_streak, is_new_milestone, new_milestone


async def get_streak(user_id: int) -> Dict:
    """Get user's streak information."""
    if not is_ready():
        return {"current": 0, "longest": 0, "milestones": []}
    
    streak_doc = await db().user_streaks.find_one({"user_id": user_id})
    if not streak_doc:
        return {"current": 0, "longest": 0, "milestones": []}
    
    # Check if streak is still active
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday = today - timedelta(days=1)
    last_activity = streak_doc.get("last_activity_date")
    
    # If last activity was before yesterday, streak is broken
    if last_activity and last_activity < yesterday:
        return {
            "current": 0,
            "longest": streak_doc.get("longest_streak", 0),
            "milestones": streak_doc.get("milestones_achieved", []),
            "broken": True
        }
    
    return {
        "current": streak_doc.get("current_streak", 0),
        "longest": streak_doc.get("longest_streak", 0),
        "milestones": streak_doc.get("milestones_achieved", []),
        "broken": False
    }


async def check_comeback_needed(user_id: int) -> bool:
    """Check if user hasn't practiced for 2+ days (comeback message needed)."""
    if not is_ready():
        return False
    
    streak_doc = await db().user_streaks.find_one({"user_id": user_id})
    if not streak_doc:
        return False
    
    last_activity = streak_doc.get("last_activity_date")
    if not last_activity:
        return False
    
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    days_inactive = (today - last_activity).days
    
    return days_inactive >= 2
