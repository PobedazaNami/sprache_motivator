"""MongoDB-based data access layer replacing previous SQLAlchemy implementation.

All methods keep the old signatures (accepting a `session` argument) for backward
compatibility with existing handlers, but the argument is ignored. Data is stored
in MongoDB using Motor. Documents are represented as simple Python objects with
attribute access where necessary.
"""
from __future__ import annotations

from typing import List, Optional, Tuple, Any, Dict
from datetime import datetime, timedelta, timezone
from bson import ObjectId

from bot.models.database import (
    UserStatus, InterfaceLanguage, LearningLanguage, WorkMode, DifficultyLevel
)
from bot.config import settings
from bot.services import mongo_service


def _now() -> datetime:
    return datetime.now(timezone.utc)


class UserModel:
    def __init__(self, doc: Dict[str, Any]):
        self._doc = doc
        self._id = doc.get("_id")  # Mongo ObjectId
        self.telegram_id = doc.get("telegram_id")
        # For backward compatibility, many handlers used numeric user.id from SQL.
        # We expose telegram_id via `id` to keep callbacks/data consistent.
        self.id = self.telegram_id
        self.username = doc.get("username")
        self.first_name = doc.get("first_name")
        self.last_name = doc.get("last_name")
        self.status: UserStatus = UserStatus(doc.get("status", UserStatus.PENDING.value))
        self.interface_language: InterfaceLanguage = InterfaceLanguage(doc.get("interface_language", InterfaceLanguage.RUSSIAN.value))
        self.learning_language: LearningLanguage = LearningLanguage(doc.get("learning_language", LearningLanguage.ENGLISH.value))
        self.work_mode: WorkMode = WorkMode(doc.get("work_mode", WorkMode.TRANSLATOR.value))
        self.difficulty_level: DifficultyLevel = DifficultyLevel(doc.get("difficulty_level", DifficultyLevel.A2.value))
        self.allow_broadcasts = doc.get("allow_broadcasts", True)
        self.daily_trainer_enabled = doc.get("daily_trainer_enabled", False)
        self.trainer_start_time = doc.get("trainer_start_time", "09:00")
        self.trainer_end_time = doc.get("trainer_end_time", "21:00")
        self.trainer_messages_per_day = doc.get("trainer_messages_per_day", 3)
        self.trainer_timezone = doc.get("trainer_timezone", "Europe/Kiev")
        self.activity_score = doc.get("activity_score", 0)
        self.translations_count = doc.get("translations_count", 0)
        self.correct_answers = doc.get("correct_answers", 0)
        self.total_answers = doc.get("total_answers", 0)
        self.tokens_used_today = doc.get("tokens_used_today", 0)
        self.last_token_reset = doc.get("last_token_reset")

    def to_update_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "interface_language": self.interface_language.value,
            "learning_language": self.learning_language.value,
            "work_mode": self.work_mode.value,
            "difficulty_level": self.difficulty_level.value,
            "allow_broadcasts": self.allow_broadcasts,
            "daily_trainer_enabled": self.daily_trainer_enabled,
            "trainer_start_time": self.trainer_start_time,
            "trainer_end_time": self.trainer_end_time,
            "trainer_messages_per_day": self.trainer_messages_per_day,
            "trainer_timezone": self.trainer_timezone,
            "activity_score": self.activity_score,
            "translations_count": self.translations_count,
            "correct_answers": self.correct_answers,
            "total_answers": self.total_answers,
            "tokens_used_today": self.tokens_used_today,
            "last_token_reset": self.last_token_reset,
        }


class UserService:
    @staticmethod
    async def _collection():
        if not mongo_service.is_ready():
            raise RuntimeError("MongoDB not initialized")
        return mongo_service.db().users

    @staticmethod
    async def get_or_create_user(session, telegram_id: int, username: str = None,
                                 first_name: str = None, last_name: str = None) -> UserModel:
        import logging
        logger = logging.getLogger(__name__)
        
        col = await UserService._collection()
        doc = await col.find_one({"telegram_id": telegram_id})
        is_admin = telegram_id in settings.admin_id_list
        
        logger.info(f"User {telegram_id} check: is_admin={is_admin}, admin_list={settings.admin_id_list}")
        
        if not doc:
            doc = {
                "telegram_id": telegram_id,
                "username": username,
                "first_name": first_name,
                "last_name": last_name,
                "status": UserStatus.APPROVED.value if is_admin else UserStatus.PENDING.value,
                "interface_language": InterfaceLanguage.RUSSIAN.value,
                "learning_language": LearningLanguage.ENGLISH.value,
                "work_mode": WorkMode.TRANSLATOR.value,
                "difficulty_level": DifficultyLevel.A2.value,
                "allow_broadcasts": True,
                "daily_trainer_enabled": False,
                "trainer_start_time": "09:00",
                "trainer_end_time": "21:00",
                "trainer_messages_per_day": 3,
                "trainer_timezone": "Europe/Kiev",
                "activity_score": 0,
                "translations_count": 0,
                "correct_answers": 0,
                "total_answers": 0,
                "tokens_used_today": 0,
                "last_token_reset": _now(),
                "created_at": _now(),
                "updated_at": _now(),
            }
            res = await col.insert_one(doc)
            doc["_id"] = res.inserted_id
        else:
            # If admin but status is not approved, auto-approve now
            logger.info(f"Existing user {telegram_id}: is_admin={is_admin}, current_status={doc.get('status')}")
            if is_admin and doc.get("status") != UserStatus.APPROVED.value:
                logger.info(f"Auto-approving admin user {telegram_id}")
                await col.update_one(
                    {"telegram_id": telegram_id},
                    {"$set": {"status": UserStatus.APPROVED.value, "updated_at": _now()}}
                )
                doc["status"] = UserStatus.APPROVED.value
        
        return UserModel(doc)

    @staticmethod
    async def update_user(session, user: UserModel, **kwargs):
        col = await UserService._collection()
        # Apply changes to object
        for k, v in kwargs.items():
            if k == "status" and isinstance(v, UserStatus):
                user.status = v
            elif k == "interface_language" and isinstance(v, InterfaceLanguage):
                user.interface_language = v
            elif k == "learning_language" and isinstance(v, LearningLanguage):
                user.learning_language = v
            elif k == "difficulty_level" and isinstance(v, DifficultyLevel):
                user.difficulty_level = v
            else:
                setattr(user, k, v)
        user.updated_at = _now()
        await col.update_one({"telegram_id": user.telegram_id}, {"$set": user.to_update_dict()})

    @staticmethod
    async def get_pending_users(session) -> List[UserModel]:
        col = await UserService._collection()
        cursor = col.find({"status": UserStatus.PENDING.value})
        return [UserModel(d) async for d in cursor]

    @staticmethod
    async def get_user_stats(session) -> dict:
        col = await UserService._collection()
        total = await col.count_documents({})
        approved = await col.count_documents({"status": UserStatus.APPROVED.value})
        pending = await col.count_documents({"status": UserStatus.PENDING.value})
        rejected = await col.count_documents({"status": UserStatus.REJECTED.value})
        return {"total": total, "approved": approved, "pending": pending, "rejected": rejected}

    @staticmethod
    async def get_users_with_trainer_enabled(session) -> List[UserModel]:
        col = await UserService._collection()
        cursor = col.find({"status": UserStatus.APPROVED.value, "daily_trainer_enabled": True})
        return [UserModel(d) async for d in cursor]

    @staticmethod
    async def get_top_users(session, limit: int = 10) -> List[UserModel]:
        col = await UserService._collection()
        cursor = col.find({"status": UserStatus.APPROVED.value}).sort("activity_score", -1).limit(limit)
        return [UserModel(d) async for d in cursor]

    @staticmethod
    async def increment_activity(session, user: UserModel, points: int = 1):
        col = await UserService._collection()
        user.activity_score += points
        await col.update_one({"telegram_id": user.telegram_id}, {"$inc": {"activity_score": points}})

    @staticmethod
    async def reset_daily_tokens_if_needed(session, user: UserModel):
        if user.last_token_reset and (_now() - user.last_token_reset > timedelta(days=1)):
            col = await UserService._collection()
            user.tokens_used_today = 0
            user.last_token_reset = _now()
            await col.update_one({"telegram_id": user.telegram_id}, {"$set": {"tokens_used_today": 0, "last_token_reset": user.last_token_reset}})

    @staticmethod
    async def get_broadcast_recipients(session) -> List[UserModel]:
        col = await UserService._collection()
        cursor = col.find({"status": UserStatus.APPROVED.value, "allow_broadcasts": True})
        return [UserModel(d) async for d in cursor]


class WordService:
    @staticmethod
    async def save_word(session, user_id: ObjectId, original: str,
                       translated: str, source_lang: str, target_lang: str) -> Dict[str, Any]:
        col = mongo_service.db().saved_words
        doc = {
            "user_id": user_id,
            "original_text": original,
            "translated_text": translated,
            "source_language": source_lang,
            "target_language": target_lang,
            "created_at": _now(),
        }
        res = await col.insert_one(doc)
        doc["_id"] = res.inserted_id
        return doc

    @staticmethod
    async def get_user_words(session, user_id: ObjectId, offset: int = 0, limit: int = 10) -> Tuple[List[Any], int]:
        col = mongo_service.db().saved_words
        total = await col.count_documents({"user_id": user_id})
        cursor = col.find({"user_id": user_id}).sort("created_at", -1).skip(offset).limit(limit)
        words = [d async for d in cursor]
        return words, total


class TranslationHistoryService:
    @staticmethod
    async def save_translation(session, user_id: ObjectId, source: str,
                               translated: str, source_lang: str, target_lang: str):
        col = mongo_service.db().translations
        doc = {
            "user_id": user_id,
            "source_text": source,
            "translated_text": translated,
            "source_language": source_lang,
            "target_language": target_lang,
            "created_at": _now(),
        }
        await col.insert_one(doc)


class TrainingService:
    @staticmethod
    async def create_session(session, user_id: ObjectId, sentence: str,
                             expected: str, difficulty: DifficultyLevel):
        col = mongo_service.db().training_sessions
        doc = {
            "user_id": user_id,
            "sentence": sentence,
            "expected_translation": expected,
            "user_translation": None,
            "is_correct": None,
            "explanation": None,
            "quality_percentage": None,
            "difficulty_level": difficulty.value,
            "created_at": _now(),
            "answered_at": None,
        }
        res = await col.insert_one(doc)
        doc["_id"] = res.inserted_id
        return doc

    @staticmethod
    async def update_session(session, training_id: Any,
                             user_translation: str, is_correct: bool, explanation: str = None,
                             quality_percentage: int = None):
        col = mongo_service.db().training_sessions
        await col.update_one({"_id": training_id}, {"$set": {
            "user_translation": user_translation,
            "is_correct": is_correct,
            "explanation": explanation,
            "quality_percentage": quality_percentage,
            "answered_at": _now(),
        }})

    @staticmethod
    async def update_daily_stats(session, user_id: ObjectId, quality_percentage: int):
        # Mirror to Mongo daily_stats collection (similar to mongo_service.update_daily_stats)
        await mongo_service.update_daily_stats(int(user_id.__str__()[:8], 16), int(quality_percentage or 0))  # lightweight uniqueness

    @staticmethod
    async def get_user_stats(session, user_id: ObjectId) -> dict:
        col = mongo_service.db().training_sessions
        total = await col.count_documents({"user_id": user_id, "answered_at": {"$ne": None}})
        correct = await col.count_documents({"user_id": user_id, "is_correct": True})
        return {"total": total, "correct": correct}


class BroadcastService:
    @staticmethod
    async def create_broadcast(session, message: str, created_by: int):
        col = mongo_service.db().broadcasts
        doc = {
            "message": message,
            "created_by": created_by,
            "sent_count": 0,
            "failed_count": 0,
            "created_at": _now(),
            "completed_at": None,
        }
        res = await col.insert_one(doc)
        doc["_id"] = res.inserted_id
        return doc

    @staticmethod
    async def update_broadcast(session, broadcast_id: Any,
                               sent: int, failed: int, completed: bool = False):
        col = mongo_service.db().broadcasts
        update_doc = {"sent_count": sent, "failed_count": failed}
        if completed:
            update_doc["completed_at"] = _now()
        await col.update_one({"_id": broadcast_id}, {"$set": update_doc})
