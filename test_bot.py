"""
Basic tests for the Sprache Motivator bot.
"""
import pytest
from unittest.mock import patch, MagicMock
import sys
import os

# Add bot directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bot'))


def test_config_import():
    """Test that configuration module can be imported."""
    from bot.config import settings
    assert settings is not None
    assert hasattr(settings, 'BOT_TOKEN')
    assert hasattr(settings, 'OPENAI_API_KEY')


def test_config_properties():
    """Test that configuration properties work correctly."""
    from bot.config import settings
    
    # Test redis_url property
    redis_url = settings.redis_url
    assert isinstance(redis_url, str)
    assert redis_url.startswith('redis://')
    
    # Test admin_id_list property
    admin_ids = settings.admin_id_list
    assert isinstance(admin_ids, list)
    
    # Test trainer_times property
    trainer_times = settings.trainer_times
    assert isinstance(trainer_times, list)
    assert len(trainer_times) > 0


def test_handlers_import():
    """Test that handler modules can be imported."""
    from bot.handlers import start, translator, trainer, settings, admin
    assert start is not None
    assert translator is not None
    assert trainer is not None
    assert settings is not None
    assert admin is not None


def test_services_import():
    """Test that service modules can be imported."""
    from bot.services import scheduler_service, translation_service
    from bot.services import redis_service, database_service, mongo_service
    assert scheduler_service is not None
    assert translation_service is not None
    assert redis_service is not None
    assert database_service is not None
    assert mongo_service is not None


def test_models_import():
    """Test that model modules can be imported."""
    from bot.models import database
    assert database is not None


def test_main_module_import():
    """Test that main module can be imported."""
    # We don't want to actually run main(), just test that it can be imported
    import bot.main
    assert bot.main is not None
    assert hasattr(bot.main, 'main')
