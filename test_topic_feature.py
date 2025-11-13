"""
Tests for the topic selection feature in trainer mode.
"""
import pytest
import sys
import os

# Add bot directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bot'))


def test_topic_enum_import():
    """Test that TrainerTopic enum can be imported."""
    from bot.models.database import TrainerTopic, TOPIC_METADATA
    assert TrainerTopic is not None
    assert TOPIC_METADATA is not None


def test_topic_enum_values():
    """Test that all topics are defined correctly."""
    from bot.models.database import TrainerTopic, TOPIC_METADATA
    
    # Check that we have 30 regular topics + 1 random
    topics = [t for t in TrainerTopic]
    assert len(topics) == 31  # 30 topics + random
    
    # Check that random topic exists
    assert TrainerTopic.RANDOM in topics
    
    # Check that each topic (except random) has metadata
    for topic in topics:
        if topic != TrainerTopic.RANDOM:
            assert topic in TOPIC_METADATA
            assert "level" in TOPIC_METADATA[topic]
            assert "number" in TOPIC_METADATA[topic]


def test_topic_levels():
    """Test that topics are correctly distributed across levels."""
    from bot.models.database import TrainerTopic, TOPIC_METADATA
    
    a2_topics = [t for t in TrainerTopic if t != TrainerTopic.RANDOM and TOPIC_METADATA[t]["level"] == "A2"]
    b1_topics = [t for t in TrainerTopic if t != TrainerTopic.RANDOM and TOPIC_METADATA[t]["level"] == "B1"]
    b2_topics = [t for t in TrainerTopic if t != TrainerTopic.RANDOM and TOPIC_METADATA[t]["level"] == "B2"]
    
    # Check correct distribution
    assert len(a2_topics) == 12  # Topics 1-12
    assert len(b1_topics) == 10  # Topics 13-22
    assert len(b2_topics) == 8   # Topics 23-30


def test_topic_localization():
    """Test that all topics have localized strings."""
    from bot.models.database import TrainerTopic
    from bot.locales.texts import get_text
    
    for topic in TrainerTopic:
        # Check Ukrainian
        topic_text_uk = get_text("uk", f"topic_{topic.value}")
        assert topic_text_uk is not None
        assert topic_text_uk != f"topic_{topic.value}"  # Should be localized, not the key
        
        # Check Russian
        topic_text_ru = get_text("ru", f"topic_{topic.value}")
        assert topic_text_ru is not None
        assert topic_text_ru != f"topic_{topic.value}"


def test_keyboard_functions():
    """Test that keyboard functions for topics exist."""
    from bot.utils.keyboards import get_topic_level_keyboard, get_topic_selection_keyboard
    
    # Test topic level keyboard
    keyboard_uk = get_topic_level_keyboard("uk")
    assert keyboard_uk is not None
    
    keyboard_ru = get_topic_level_keyboard("ru")
    assert keyboard_ru is not None
    
    # Test topic selection keyboards for each level
    for level in ["A2", "B1", "B2"]:
        keyboard = get_topic_selection_keyboard("uk", level)
        assert keyboard is not None


def test_user_model_has_topic_field():
    """Test that UserModel includes trainer_topic field."""
    from bot.services.database_service import UserModel
    from bot.models.database import TrainerTopic
    
    # Create a mock document
    mock_doc = {
        "_id": "test_id",
        "telegram_id": 12345,
        "username": "test_user",
        "first_name": "Test",
        "last_name": "User",
        "status": "approved",
        "interface_language": "uk",
        "learning_language": "de",
        "work_mode": "translator",
        "difficulty_level": "A2",
        "trainer_topic": TrainerTopic.PERSONAL_INFO.value,
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
    }
    
    user = UserModel(mock_doc)
    assert hasattr(user, 'trainer_topic')
    assert user.trainer_topic == TrainerTopic.PERSONAL_INFO


def test_translation_service_topic_parameter():
    """Test that generate_sentence accepts topic parameter."""
    from bot.services.translation_service import TranslationService
    import inspect
    
    # Check that generate_sentence method accepts topic parameter
    sig = inspect.signature(TranslationService.generate_sentence)
    params = sig.parameters
    assert 'topic' in params


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
