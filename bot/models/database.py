from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Enum as SQLEnum, BigInteger
from sqlalchemy.sql import func
from datetime import datetime
from typing import AsyncGenerator
import enum

from bot.config import settings


# Create async engine
engine = create_async_engine(settings.database_url, echo=False)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Hardcoded admin approval override: ensure admin ID is always approved
HARDCODED_ADMIN_ID = 662790795


class Base(DeclarativeBase):
    pass


class UserStatus(enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class InterfaceLanguage(enum.Enum):
    UKRAINIAN = "uk"
    RUSSIAN = "ru"


class LearningLanguage(enum.Enum):
    ENGLISH = "en"
    GERMAN = "de"


class WorkMode(enum.Enum):
    TRANSLATOR = "translator"
    DAILY_TRAINER = "daily_trainer"


class DifficultyLevel(enum.Enum):
    A2 = "A2"
    B1 = "B1"
    B2 = "B2"
    COMBINED = "A2-B2"


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(255))
    first_name = Column(String(255))
    last_name = Column(String(255))
    
    status = Column(SQLEnum(UserStatus), default=UserStatus.PENDING, nullable=False)
    interface_language = Column(SQLEnum(InterfaceLanguage), default=InterfaceLanguage.RUSSIAN, nullable=False)
    learning_language = Column(SQLEnum(LearningLanguage), default=LearningLanguage.ENGLISH, nullable=False)
    work_mode = Column(SQLEnum(WorkMode), default=WorkMode.TRANSLATOR, nullable=False)
    difficulty_level = Column(SQLEnum(DifficultyLevel), default=DifficultyLevel.A2)
    
    # Preferences
    allow_broadcasts = Column(Boolean, default=True)
    daily_trainer_enabled = Column(Boolean, default=False)
    
    # Trainer settings (новые поля)
    trainer_start_time = Column(String(5), default="09:00")  # HH:MM format, Kyiv timezone
    trainer_end_time = Column(String(5), default="21:00")    # HH:MM format, Kyiv timezone
    trainer_messages_per_day = Column(Integer, default=3)    # 1-10 messages per day
    trainer_timezone = Column(String(50), default="Europe/Kiev")
    
    # Statistics
    activity_score = Column(Integer, default=0)
    translations_count = Column(Integer, default=0)
    correct_answers = Column(Integer, default=0)
    total_answers = Column(Integer, default=0)
    tokens_used_today = Column(Integer, default=0)
    last_token_reset = Column(DateTime(timezone=True), server_default=func.now())
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class SavedWord(Base):
    __tablename__ = "saved_words"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    original_text = Column(String(500), nullable=False)
    translated_text = Column(String(500), nullable=False)
    source_language = Column(String(10), nullable=False)
    target_language = Column(String(10), nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Translation(Base):
    __tablename__ = "translations"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    
    source_text = Column(String(1000), nullable=False)
    translated_text = Column(Text, nullable=False)
    source_language = Column(String(10), nullable=False)
    target_language = Column(String(10), nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class TrainingSession(Base):
    __tablename__ = "training_sessions"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    sentence = Column(Text, nullable=False)
    expected_translation = Column(Text, nullable=False)
    user_translation = Column(Text)
    is_correct = Column(Boolean)
    explanation = Column(Text)
    quality_percentage = Column(Integer)  # 0-100% качество перевода от ИИ
    
    difficulty_level = Column(SQLEnum(DifficultyLevel), nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    answered_at = Column(DateTime(timezone=True))


class DailyStats(Base):
    """Ежедневная статистика пользователя"""
    __tablename__ = "daily_stats"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(DateTime(timezone=True), nullable=False, index=True)  # Дата статистики
    
    total_tasks = Column(Integer, default=0)  # Всего заданий
    completed_tasks = Column(Integer, default=0)  # Выполнено заданий
    average_quality = Column(Integer, default=0)  # Средний процент качества (0-100)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        # Уникальный индекс: один пользователь - одна запись на день
        {'sqlite_autoincrement': True},
    )


class WeeklyStats(Base):
    """Еженедельная статистика пользователя"""
    __tablename__ = "weekly_stats"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    week_start = Column(DateTime(timezone=True), nullable=False, index=True)  # Начало недели (понедельник)
    
    total_tasks = Column(Integer, default=0)
    completed_tasks = Column(Integer, default=0)
    average_quality = Column(Integer, default=0)  # Средний процент за неделю
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Broadcast(Base):
    __tablename__ = "broadcasts"
    
    id = Column(Integer, primary_key=True)
    message = Column(Text, nullable=False)
    sent_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    
    created_by = Column(BigInteger, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Ensure admin user exists and is approved
        from sqlalchemy import select
        async with async_session_maker() as session:
            result = await session.execute(select(User).where(User.telegram_id == HARDCODED_ADMIN_ID))
            admin_user = result.scalar_one_or_none()
            if not admin_user:
                admin_user = User(telegram_id=HARDCODED_ADMIN_ID, status=UserStatus.APPROVED)
                session.add(admin_user)
                await session.commit()
            elif admin_user.status != UserStatus.APPROVED:
                admin_user.status = UserStatus.APPROVED
                await session.commit()


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get an async database session.
    
    This is an async context manager that yields a database session.
    It should be used with 'async with' statement for proper session
    management and automatic cleanup:
    
    Example:
        async with async_session_maker() as session:
            # Use session here
            result = await session.execute(query)
    
    Yields:
        AsyncSession: Database session that will be automatically closed
    """
    async with async_session_maker() as session:
        yield session
