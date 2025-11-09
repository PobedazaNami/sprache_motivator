"""
MongoDB database models and enums.
Using Motor (async MongoDB driver) for all database operations.
"""
from enum import Enum

# Hardcoded admin approval override
HARDCODED_ADMIN_ID = 662790795


class UserStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class InterfaceLanguage(str, Enum):
    UKRAINIAN = "uk"
    RUSSIAN = "ru"


class LearningLanguage(str, Enum):
    ENGLISH = "en"
    GERMAN = "de"


class WorkMode(str, Enum):
    TRANSLATOR = "translator"
    DAILY_TRAINER = "daily_trainer"


class DifficultyLevel(str, Enum):
    A2 = "A2"
    B1 = "B1"
    B2 = "B2"
    COMBINED = "A2-B2"


# ---------------------------------------------------------------------------
# Compatibility helper: dummy async_session_maker to keep existing handlers
# "async with async_session_maker() as session:" will yield None.
# All database logic now goes through MongoDB services and ignores session.
# ---------------------------------------------------------------------------
def async_session_maker():
    class _Dummy:
        async def __aenter__(self):
            return None
        async def __aexit__(self, exc_type, exc, tb):
            return False
    return _Dummy()


async def init_db():
    """Initialize MongoDB database connection"""
    from bot.services import mongo_service
    await mongo_service.init()
