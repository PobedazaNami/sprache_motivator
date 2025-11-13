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


class TrainerTopic(str, Enum):
    """Topics for trainer sentences organized by CEFR level"""
    # A2 Topics (1-12)
    PERSONAL_INFO = "personal_info"  # 1. Persönliche Informationen und Vorstellung
    FAMILY_FRIENDS = "family_friends"  # 2. Familie und Freunde
    HOME_DAILY = "home_daily"  # 3. Wohnung und Alltag
    LEISURE_HOBBIES = "leisure_hobbies"  # 4. Freizeit und Hobbys
    SHOPPING_MONEY = "shopping_money"  # 5. Einkaufen und Geld
    FOOD_DRINK = "food_drink"  # 6. Essen und Trinken
    HEALTH_DOCTOR = "health_doctor"  # 7. Gesundheit und Arztbesuch
    TRANSPORT = "transport"  # 8. Verkehr und Transport
    TRAVEL_VACATION = "travel_vacation"  # 9. Reisen und Urlaub
    WEATHER_SEASONS = "weather_seasons"  # 10. Wetter und Jahreszeiten
    SCHOOL_LEARNING = "school_learning"  # 11. Schule und Lernen
    CELEBRATIONS = "celebrations"  # 12. Feste und Feiertage
    
    # B1 Topics (13-22)
    WORK_CAREER = "work_career"  # 13. Arbeit und Beruf
    JOB_APPLICATION = "job_application"  # 14. Bewerbung und Lebenslauf
    RESIDENCE_NEIGHBORHOOD = "residence_neighborhood"  # 15. Wohnort und Nachbarschaft
    LEISURE_MEDIA = "leisure_media"  # 16. Freizeit und Medien
    FOOD_NUTRITION = "food_nutrition"  # 17. Essen, Trinken und Ernährung
    TRAVEL_TRAFFIC = "travel_traffic"  # 18. Reisen und Verkehr
    ENVIRONMENT_NATURE = "environment_nature"  # 19. Umwelt und Natur
    SOCIETY_COEXISTENCE = "society_coexistence"  # 20. Gesellschaft und Zusammenleben
    HEALTH_LIFESTYLE = "health_lifestyle"  # 21. Gesundheit und Lebensstil
    FASHION_CLOTHING = "fashion_clothing"  # 22. Mode und Kleidung
    
    # B2 Topics (23-30)
    TECHNOLOGY_DIGITALIZATION = "technology_digitalization"  # 23. Technologie und Digitalisierung
    MEDIA_ADVERTISING = "media_advertising"  # 24. Medien, Werbung und Konsum
    FUTURE_DREAMS = "future_dreams"  # 25. Zukunft und Träume
    SOCIAL_PROBLEMS = "social_problems"  # 26. Gesellschaftliche Probleme
    CULTURE_IDENTITY = "culture_identity"  # 27. Kultur und Identität
    SCIENCE_INNOVATION = "science_innovation"  # 28. Wissenschaft und Innovation
    ENVIRONMENT_CLIMATE = "environment_climate"  # 29. Umwelt und Klimawandel
    FUTURE_WORK = "future_work"  # 30. Arbeit der Zukunft
    
    # Special option
    RANDOM = "random"


# Topic metadata: level and topic number
TOPIC_METADATA = {
    # A2 Topics
    TrainerTopic.PERSONAL_INFO: {"level": "A2", "number": 1},
    TrainerTopic.FAMILY_FRIENDS: {"level": "A2", "number": 2},
    TrainerTopic.HOME_DAILY: {"level": "A2", "number": 3},
    TrainerTopic.LEISURE_HOBBIES: {"level": "A2", "number": 4},
    TrainerTopic.SHOPPING_MONEY: {"level": "A2", "number": 5},
    TrainerTopic.FOOD_DRINK: {"level": "A2", "number": 6},
    TrainerTopic.HEALTH_DOCTOR: {"level": "A2", "number": 7},
    TrainerTopic.TRANSPORT: {"level": "A2", "number": 8},
    TrainerTopic.TRAVEL_VACATION: {"level": "A2", "number": 9},
    TrainerTopic.WEATHER_SEASONS: {"level": "A2", "number": 10},
    TrainerTopic.SCHOOL_LEARNING: {"level": "A2", "number": 11},
    TrainerTopic.CELEBRATIONS: {"level": "A2", "number": 12},
    
    # B1 Topics
    TrainerTopic.WORK_CAREER: {"level": "B1", "number": 13},
    TrainerTopic.JOB_APPLICATION: {"level": "B1", "number": 14},
    TrainerTopic.RESIDENCE_NEIGHBORHOOD: {"level": "B1", "number": 15},
    TrainerTopic.LEISURE_MEDIA: {"level": "B1", "number": 16},
    TrainerTopic.FOOD_NUTRITION: {"level": "B1", "number": 17},
    TrainerTopic.TRAVEL_TRAFFIC: {"level": "B1", "number": 18},
    TrainerTopic.ENVIRONMENT_NATURE: {"level": "B1", "number": 19},
    TrainerTopic.SOCIETY_COEXISTENCE: {"level": "B1", "number": 20},
    TrainerTopic.HEALTH_LIFESTYLE: {"level": "B1", "number": 21},
    TrainerTopic.FASHION_CLOTHING: {"level": "B1", "number": 22},
    
    # B2 Topics
    TrainerTopic.TECHNOLOGY_DIGITALIZATION: {"level": "B2", "number": 23},
    TrainerTopic.MEDIA_ADVERTISING: {"level": "B2", "number": 24},
    TrainerTopic.FUTURE_DREAMS: {"level": "B2", "number": 25},
    TrainerTopic.SOCIAL_PROBLEMS: {"level": "B2", "number": 26},
    TrainerTopic.CULTURE_IDENTITY: {"level": "B2", "number": 27},
    TrainerTopic.SCIENCE_INNOVATION: {"level": "B2", "number": 28},
    TrainerTopic.ENVIRONMENT_CLIMATE: {"level": "B2", "number": 29},
    TrainerTopic.FUTURE_WORK: {"level": "B2", "number": 30},
    
    # Special
    TrainerTopic.RANDOM: {"level": "ALL", "number": 0},
}


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
