from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from bot.models.database import (
    User, SavedWord, Translation, TrainingSession, Broadcast,
    UserStatus, InterfaceLanguage, LearningLanguage, WorkMode, DifficultyLevel
)
from bot.config import settings
from bot.services import mongo_service


class UserService:
    @staticmethod
    async def get_or_create_user(session: AsyncSession, telegram_id: int, username: str = None, 
                                  first_name: str = None, last_name: str = None) -> User:
        """Get existing user or create new one"""
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
        
        return user
    
    @staticmethod
    async def update_user(session: AsyncSession, user: User, **kwargs):
        """Update user fields"""
        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)
        await session.commit()
        await session.refresh(user)
    
    @staticmethod
    async def get_pending_users(session: AsyncSession) -> List[User]:
        """Get all users pending approval"""
        result = await session.execute(
            select(User).where(User.status == UserStatus.PENDING)
        )
        return result.scalars().all()
    
    @staticmethod
    async def get_user_stats(session: AsyncSession) -> dict:
        """Get user statistics"""
        total = await session.execute(select(func.count(User.id)))
        approved = await session.execute(
            select(func.count(User.id)).where(User.status == UserStatus.APPROVED)
        )
        pending = await session.execute(
            select(func.count(User.id)).where(User.status == UserStatus.PENDING)
        )
        rejected = await session.execute(
            select(func.count(User.id)).where(User.status == UserStatus.REJECTED)
        )
        
        return {
            "total": total.scalar(),
            "approved": approved.scalar(),
            "pending": pending.scalar(),
            "rejected": rejected.scalar()
        }
    
    @staticmethod
    async def get_users_with_trainer_enabled(session: AsyncSession) -> List[User]:
        """Get all users with trainer enabled"""
        result = await session.execute(
            select(User).where(
                User.status == UserStatus.APPROVED,
                User.daily_trainer_enabled == True
            )
        )
        return result.scalars().all()
    
    @staticmethod
    async def get_top_users(session: AsyncSession, limit: int = 10) -> List[User]:
        """Get top users by activity score"""
        result = await session.execute(
            select(User)
            .where(User.status == UserStatus.APPROVED)
            .order_by(User.activity_score.desc())
            .limit(limit)
        )
        return result.scalars().all()
    
    @staticmethod
    async def increment_activity(session: AsyncSession, user: User, points: int = 1):
        """Increment user activity score"""
        user.activity_score += points
        await session.commit()
    
    @staticmethod
    async def reset_daily_tokens_if_needed(session: AsyncSession, user: User):
        """Reset daily token counter if 24 hours passed"""
        if user.last_token_reset:
            if datetime.now() - user.last_token_reset > timedelta(days=1):
                user.tokens_used_today = 0
                user.last_token_reset = datetime.now()
                await session.commit()
    
    @staticmethod
    async def get_broadcast_recipients(session: AsyncSession) -> List[User]:
        """Get users who allow broadcasts"""
        result = await session.execute(
            select(User).where(
                User.status == UserStatus.APPROVED,
                User.allow_broadcasts == True
            )
        )
        return result.scalars().all()


class WordService:
    @staticmethod
    async def save_word(session: AsyncSession, user_id: int, original: str, 
                       translated: str, source_lang: str, target_lang: str) -> SavedWord:
        """Save a word to user's collection"""
        word = SavedWord(
            user_id=user_id,
            original_text=original,
            translated_text=translated,
            source_language=source_lang,
            target_language=target_lang
        )
        session.add(word)
        await session.commit()
        await session.refresh(word)
        return word
    
    @staticmethod
    async def get_user_words(session: AsyncSession, user_id: int, 
                            offset: int = 0, limit: int = 10) -> Tuple[List[SavedWord], int]:
        """Get user's saved words with pagination"""
        # Get total count
        total = await session.execute(
            select(func.count(SavedWord.id)).where(SavedWord.user_id == user_id)
        )
        total_count = total.scalar()
        
        # Get words
        result = await session.execute(
            select(SavedWord)
            .where(SavedWord.user_id == user_id)
            .order_by(SavedWord.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        words = result.scalars().all()
        
        return words, total_count


class TranslationHistoryService:
    @staticmethod
    async def save_translation(session: AsyncSession, user_id: int, source: str,
                               translated: str, source_lang: str, target_lang: str):
        """Save translation to history"""
        translation = Translation(
            user_id=user_id,
            source_text=source,
            translated_text=translated,
            source_language=source_lang,
            target_language=target_lang
        )
        session.add(translation)
        await session.commit()


class TrainingService:
    @staticmethod
    async def create_session(session: AsyncSession, user_id: int, sentence: str,
                            expected: str, difficulty: DifficultyLevel) -> TrainingSession:
        """Create a new training session"""
        training = TrainingSession(
            user_id=user_id,
            sentence=sentence,
            expected_translation=expected,
            difficulty_level=difficulty
        )
        session.add(training)
        await session.commit()
        await session.refresh(training)
        return training
    
    @staticmethod
    async def update_session(session: AsyncSession, training_id: int, 
                            user_translation: str, is_correct: bool, explanation: str = None,
                            quality_percentage: int = None):
        """Update training session with user's answer and quality"""
        await session.execute(
            update(TrainingSession)
            .where(TrainingSession.id == training_id)
            .values(
                user_translation=user_translation,
                is_correct=is_correct,
                explanation=explanation,
                quality_percentage=quality_percentage,
                answered_at=datetime.now()
            )
        )
        await session.commit()
    
    @staticmethod
    async def update_daily_stats(session: AsyncSession, user_id: int, quality_percentage: int):
        """Update daily statistics for user"""
        from datetime import datetime, timezone
        from bot.models.database import DailyStats
        
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Get or create today's stats
        result = await session.execute(
            select(DailyStats).where(
                DailyStats.user_id == user_id,
                DailyStats.date == today
            )
        )
        stats = result.scalar_one_or_none()
        
        if not stats:
            stats = DailyStats(
                user_id=user_id,
                date=today,
                total_tasks=0,
                completed_tasks=0,
                average_quality=0
            )
            session.add(stats)
        
        # Update stats
        stats.total_tasks += 1
        stats.completed_tasks += 1
        
        # Recalculate average quality
        old_total = stats.average_quality * (stats.completed_tasks - 1)
        stats.average_quality = int((old_total + quality_percentage) / stats.completed_tasks)
        
        await session.commit()
        # Mirror to MongoDB if enabled
        if settings.mongo_enabled and mongo_service.is_ready():
            try:
                await mongo_service.update_daily_stats(user_id, int(quality_percentage or 0))
            except Exception:
                # Do not fail primary path on Mongo errors
                pass
    
    @staticmethod
    async def get_user_stats(session: AsyncSession, user_id: int) -> dict:
        """Get user's training statistics"""
        total = await session.execute(
            select(func.count(TrainingSession.id))
            .where(TrainingSession.user_id == user_id, TrainingSession.answered_at.isnot(None))
        )
        correct = await session.execute(
            select(func.count(TrainingSession.id))
            .where(TrainingSession.user_id == user_id, TrainingSession.is_correct == True)
        )
        
        return {
            "total": total.scalar(),
            "correct": correct.scalar()
        }


class BroadcastService:
    @staticmethod
    async def create_broadcast(session: AsyncSession, message: str, created_by: int) -> Broadcast:
        """Create a new broadcast"""
        broadcast = Broadcast(
            message=message,
            created_by=created_by
        )
        session.add(broadcast)
        await session.commit()
        await session.refresh(broadcast)
        return broadcast
    
    @staticmethod
    async def update_broadcast(session: AsyncSession, broadcast_id: int, 
                              sent: int, failed: int, completed: bool = False):
        """Update broadcast statistics"""
        values = {
            "sent_count": sent,
            "failed_count": failed
        }
        if completed:
            values["completed_at"] = datetime.now()
        
        await session.execute(
            update(Broadcast)
            .where(Broadcast.id == broadcast_id)
            .values(**values)
        )
        await session.commit()
