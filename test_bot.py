"""
Basic tests for Sprache Motivator Bot

These tests validate the core functionality without requiring external services.
"""

import pytest
from bot.locales.texts import get_text, LOCALES


class TestLocalization:
    """Test localization functionality"""
    
    def test_get_text_ukrainian(self):
        """Test Ukrainian text retrieval"""
        text = get_text("uk", "welcome")
        assert "Вітаємо" in text
        assert "Sprache Motivator" in text
    
    def test_get_text_russian(self):
        """Test Russian text retrieval"""
        text = get_text("ru", "welcome")
        assert "Добро пожаловать" in text
        assert "Sprache Motivator" in text
    
    def test_get_text_with_params(self):
        """Test text retrieval with parameters"""
        text = get_text("ru", "total_users", total=100, approved=80, pending=15, rejected=5)
        assert "100" in text
        assert "80" in text
        assert "15" in text
        assert "5" in text
    
    def test_locales_completeness(self):
        """Ensure both languages have the same keys"""
        uk_keys = set(LOCALES["uk"].keys())
        ru_keys = set(LOCALES["ru"].keys())
        assert uk_keys == ru_keys, "Ukrainian and Russian locales should have same keys"
    
    def test_fallback_to_russian(self):
        """Test fallback to Russian for unknown language"""
        text = get_text("unknown_lang", "welcome")
        # Should fallback to Russian
        assert "Добро пожаловать" in text


class TestConfig:
    """Test configuration handling"""
    
    def test_config_import(self):
        """Test that config can be imported"""
        from bot.config import Settings
        settings = Settings(
            BOT_TOKEN="test_token",
            OPENAI_API_KEY="test_key",
            ADMIN_IDS="123,456"
        )
        assert settings.BOT_TOKEN == "test_token"
        assert settings.OPENAI_API_KEY == "test_key"
    
    def test_admin_id_list_parsing(self):
        """Test admin ID list parsing"""
        from bot.config import Settings
        settings = Settings(
            BOT_TOKEN="test",
            OPENAI_API_KEY="test",
            ADMIN_IDS="123,456,789"
        )
        assert settings.admin_id_list == [123, 456, 789]
    
    def test_trainer_times_parsing(self):
        """Test trainer times parsing"""
        from bot.config import Settings
        settings = Settings(
            BOT_TOKEN="test",
            OPENAI_API_KEY="test",
            DAILY_TRAINER_TIMES="09:00,15:00,21:00"
        )
        assert settings.trainer_times == ["09:00", "15:00", "21:00"]
    
    def test_database_url_generation(self):
        """Test database URL generation"""
        from bot.config import Settings
        settings = Settings(
            BOT_TOKEN="test",
            OPENAI_API_KEY="test",
            POSTGRES_USER="user",
            POSTGRES_PASSWORD="pass",
            POSTGRES_HOST="localhost",
            POSTGRES_PORT=5432,
            POSTGRES_DB="testdb"
        )
        expected = "postgresql+asyncpg://user:pass@localhost:5432/testdb"
        assert settings.database_url == expected


class TestModels:
    """Test database models"""
    
    def test_user_status_enum(self):
        """Test UserStatus enum"""
        from bot.models.database import UserStatus
        assert UserStatus.PENDING.value == "pending"
        assert UserStatus.APPROVED.value == "approved"
        assert UserStatus.REJECTED.value == "rejected"
    
    def test_interface_language_enum(self):
        """Test InterfaceLanguage enum"""
        from bot.models.database import InterfaceLanguage
        assert InterfaceLanguage.UKRAINIAN.value == "uk"
        assert InterfaceLanguage.RUSSIAN.value == "ru"
    
    def test_learning_language_enum(self):
        """Test LearningLanguage enum"""
        from bot.models.database import LearningLanguage
        assert LearningLanguage.ENGLISH.value == "en"
        assert LearningLanguage.GERMAN.value == "de"
    
    def test_difficulty_level_enum(self):
        """Test DifficultyLevel enum"""
        from bot.models.database import DifficultyLevel
        assert DifficultyLevel.A2.value == "A2"
        assert DifficultyLevel.B1.value == "B1"
        assert DifficultyLevel.B2.value == "B2"
        assert DifficultyLevel.COMBINED.value == "A2-B2"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
