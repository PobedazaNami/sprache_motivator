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


# Topic metadata: level, topic number and localized names for DE/EN
TOPIC_METADATA = {
    # A2 Topics
    TrainerTopic.PERSONAL_INFO: {
        "level": "A2", "number": 1,
        "de": "1. Persönliche Informationen und Vorstellung",
        "en": "1. Personal information and introduction",
    },
    TrainerTopic.FAMILY_FRIENDS: {
        "level": "A2", "number": 2,
        "de": "2. Familie und Freunde",
        "en": "2. Family and friends",
    },
    TrainerTopic.HOME_DAILY: {
        "level": "A2", "number": 3,
        "de": "3. Wohnung und Alltag",
        "en": "3. Home and daily life",
    },
    TrainerTopic.LEISURE_HOBBIES: {
        "level": "A2", "number": 4,
        "de": "4. Freizeit und Hobbys",
        "en": "4. Leisure and hobbies",
    },
    TrainerTopic.SHOPPING_MONEY: {
        "level": "A2", "number": 5,
        "de": "5. Einkaufen und Geld",
        "en": "5. Shopping and money",
    },
    TrainerTopic.FOOD_DRINK: {
        "level": "A2", "number": 6,
        "de": "6. Essen und Trinken",
        "en": "6. Food and drink",
    },
    TrainerTopic.HEALTH_DOCTOR: {
        "level": "A2", "number": 7,
        "de": "7. Gesundheit und Arztbesuch",
        "en": "7. Health and doctor visits",
    },
    TrainerTopic.TRANSPORT: {
        "level": "A2", "number": 8,
        "de": "8. Verkehr und Transport",
        "en": "8. Traffic and transport",
    },
    TrainerTopic.TRAVEL_VACATION: {
        "level": "A2", "number": 9,
        "de": "9. Reisen und Urlaub",
        "en": "9. Travel and vacation",
    },
    TrainerTopic.WEATHER_SEASONS: {
        "level": "A2", "number": 10,
        "de": "10. Wetter und Jahreszeiten",
        "en": "10. Weather and seasons",
    },
    TrainerTopic.SCHOOL_LEARNING: {
        "level": "A2", "number": 11,
        "de": "11. Schule und Lernen",
        "en": "11. School and learning",
    },
    TrainerTopic.CELEBRATIONS: {
        "level": "A2", "number": 12,
        "de": "12. Feste und Feiertage",
        "en": "12. Celebrations and holidays",
    },
    
    # B1 Topics
    TrainerTopic.WORK_CAREER: {
        "level": "B1", "number": 13,
        "de": "13. Arbeit und Beruf",
        "en": "13. Work and career",
    },
    TrainerTopic.JOB_APPLICATION: {
        "level": "B1", "number": 14,
        "de": "14. Bewerbung und Lebenslauf",
        "en": "14. Job application and CV",
    },
    TrainerTopic.RESIDENCE_NEIGHBORHOOD: {
        "level": "B1", "number": 15,
        "de": "15. Wohnort und Nachbarschaft",
        "en": "15. Residence and neighborhood",
    },
    TrainerTopic.LEISURE_MEDIA: {
        "level": "B1", "number": 16,
        "de": "16. Freizeit und Medien",
        "en": "16. Leisure and media",
    },
    TrainerTopic.FOOD_NUTRITION: {
        "level": "B1", "number": 17,
        "de": "17. Essen, Trinken und Ernährung",
        "en": "17. Food, drink and nutrition",
    },
    TrainerTopic.TRAVEL_TRAFFIC: {
        "level": "B1", "number": 18,
        "de": "18. Reisen und Verkehr",
        "en": "18. Travel and traffic",
    },
    TrainerTopic.ENVIRONMENT_NATURE: {
        "level": "B1", "number": 19,
        "de": "19. Umwelt und Natur",
        "en": "19. Environment and nature",
    },
    TrainerTopic.SOCIETY_COEXISTENCE: {
        "level": "B1", "number": 20,
        "de": "20. Gesellschaft und Zusammenleben",
        "en": "20. Society and coexistence",
    },
    TrainerTopic.HEALTH_LIFESTYLE: {
        "level": "B1", "number": 21,
        "de": "21. Gesundheit und Lebensstil",
        "en": "21. Health and lifestyle",
    },
    TrainerTopic.FASHION_CLOTHING: {
        "level": "B1", "number": 22,
        "de": "22. Mode und Kleidung",
        "en": "22. Fashion and clothing",
    },
    
    # B2 Topics
    TrainerTopic.TECHNOLOGY_DIGITALIZATION: {
        "level": "B2", "number": 23,
        "de": "23. Technologie und Digitalisierung",
        "en": "23. Technology and digitalization",
    },
    TrainerTopic.MEDIA_ADVERTISING: {
        "level": "B2", "number": 24,
        "de": "24. Medien, Werbung und Konsum",
        "en": "24. Media, advertising and consumption",
    },
    TrainerTopic.FUTURE_DREAMS: {
        "level": "B2", "number": 25,
        "de": "25. Zukunft und Träume",
        "en": "25. Future and dreams",
    },
    TrainerTopic.SOCIAL_PROBLEMS: {
        "level": "B2", "number": 26,
        "de": "26. Gesellschaftliche Probleme",
        "en": "26. Social problems",
    },
    TrainerTopic.CULTURE_IDENTITY: {
        "level": "B2", "number": 27,
        "de": "27. Kultur und Identität",
        "en": "27. Culture and identity",
    },
    TrainerTopic.SCIENCE_INNOVATION: {
        "level": "B2", "number": 28,
        "de": "28. Wissenschaft und Innovation",
        "en": "28. Science and innovation",
    },
    TrainerTopic.ENVIRONMENT_CLIMATE: {
        "level": "B2", "number": 29,
        "de": "29. Umwelt und Klimawandel",
        "en": "29. Environment and climate change",
    },
    TrainerTopic.FUTURE_WORK: {
        "level": "B2", "number": 30,
        "de": "30. Arbeit der Zukunft",
        "en": "30. Work of the future",
    },
    
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
