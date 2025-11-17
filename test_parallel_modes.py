"""
Test for parallel mode operation - translator and trainer modes should not interfere.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, ANY
import sys
import os
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, User

# Add bot directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bot'))


@pytest.mark.asyncio
async def test_translator_checks_training_state():
    """Test that translator handler checks for active training sessions."""
    from bot.handlers.translator import process_translation, TranslatorStates
    from bot.services.redis_service import RedisService
    
    # Mock message
    message = MagicMock(spec=Message)
    message.from_user = MagicMock(spec=User)
    message.from_user.id = 12345
    message.text = "Test translation"
    message.answer = AsyncMock()
    
    # Mock FSM context with translator state
    state = MagicMock(spec=FSMContext)
    state.get_data = AsyncMock(return_value={
        "lang": "uk",
        "learning_lang": "en",
        "user_id": 1
    })
    state.clear = AsyncMock()
    
    # Mock RedisService to return active training session
    with patch('bot.services.redis_service.redis_service') as mock_redis:
        mock_redis.get_user_state = AsyncMock(return_value={
            "state": "awaiting_training_answer",
            "data": {"training_id": "507f1f77bcf86cd799439011"}
        })
        mock_redis.set = AsyncMock()  # Mock the set method
        
        # Call the handler
        await process_translation(message, state)
        
        # Verify that state was cleared (to let trainer handle it)
        state.clear.assert_called_once()
        
        # Verify that translator state was saved
        mock_redis.set.assert_called_once()
        
        # Verify that translation was NOT processed
        message.answer.assert_not_called()
    
    print("✓ Translator correctly defers to trainer when training session is active")


@pytest.mark.asyncio
async def test_translator_processes_when_no_training():
    """Test that translator works normally when no training session is active."""
    from bot.handlers.translator import process_translation, TranslatorStates
    
    # Mock message
    message = MagicMock(spec=Message)
    message.from_user = MagicMock(spec=User)
    message.from_user.id = 12345
    message.text = "Hello world"
    message.answer = AsyncMock()
    
    # Mock FSM context
    state = MagicMock(spec=FSMContext)
    state.get_data = AsyncMock(return_value={
        "lang": "uk",
        "learning_lang": "en",
        "user_id": 1
    })
    state.clear = AsyncMock()
    state.update_data = AsyncMock()
    state.set_state = AsyncMock()
    
    # Mock dependencies
    with patch('bot.services.redis_service.redis_service') as mock_redis, \
         patch('bot.handlers.translator.async_session_maker') as mock_session, \
         patch('bot.handlers.translator.translation_service') as mock_translation, \
         patch('bot.handlers.translator.UserService') as mock_user_service, \
         patch('bot.handlers.translator.TranslationHistoryService') as mock_history:
        
        # No training session
        mock_redis.get_user_state = AsyncMock(return_value=None)
        
        # Mock user
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.translations_count = 0
        mock_user.trial_activated = True
        mock_user.subscription_active = True
        mock_user_service.get_or_create_user = AsyncMock(return_value=mock_user)
        mock_user_service.increment_activity = AsyncMock()
        mock_user_service.is_trial_expired.return_value = False
        
        # Mock translation
        mock_translation.translate = AsyncMock(return_value=("Привіт світ", 100))
        mock_history.save_translation = AsyncMock()
        
        # Mock session
        mock_session_instance = AsyncMock()
        mock_session_instance.__aenter__ = AsyncMock(return_value=mock_session_instance)
        mock_session_instance.__aexit__ = AsyncMock(return_value=None)
        mock_session.return_value = mock_session_instance
        
        # Call the handler
        await process_translation(message, state)
        
        # Verify state was NOT cleared
        state.clear.assert_not_called()
        
        # Verify translation was processed
        mock_translation.translate.assert_called_once()
        message.answer.assert_called_once()
    
    print("✓ Translator processes translations normally when no training session")


@pytest.mark.asyncio
async def test_trainer_handler_processes_with_cleared_state():
    """Test that trainer handler can process messages even when FSM state is cleared."""
    from bot.handlers.trainer import check_training_answer
    
    # Mock message
    message = MagicMock(spec=Message)
    message.from_user = MagicMock(spec=User)
    message.from_user.id = 12345
    message.text = "My training answer"
    message.answer = AsyncMock()
    
    # Mock Redis with active training session
    with patch('bot.services.redis_service.redis_service') as mock_redis, \
         patch('bot.handlers.trainer.async_session_maker') as mock_session, \
         patch('bot.handlers.trainer.mongo_service') as mock_mongo, \
         patch('bot.handlers.trainer.translation_service') as mock_translation, \
         patch('bot.handlers.trainer.UserService') as mock_user_service, \
         patch('bot.handlers.trainer.TrainingService') as mock_training_service:
        
        # Active training session in Redis
        mock_redis.get_user_state = AsyncMock(return_value={
            "state": "awaiting_training_answer",
            "data": {"training_id": "507f1f77bcf86cd799439011"}
        })
        mock_redis.clear_user_state = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)  # No saved translator state
        mock_redis.set = AsyncMock()
        
        # Mock MongoDB training session
        from bson import ObjectId
        training_id = ObjectId("507f1f77bcf86cd799439011")
        mock_training_col = MagicMock()
        mock_training_col.find_one = AsyncMock(return_value={
            "_id": training_id,
            "sentence": "Test sentence",
            "expected_translation": "Тестове речення"
        })
        mock_mongo.db = MagicMock(return_value=MagicMock(
            training_sessions=mock_training_col
        ))
        
        # Mock user
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.interface_language.value = "uk"
        mock_user.learning_language.value = "en"
        mock_user.total_answers = 0
        mock_user.correct_answers = 0
        mock_user_service.get_or_create_user = AsyncMock(return_value=mock_user)
        mock_user_service.update_user = AsyncMock()
        mock_user_service.increment_activity = AsyncMock()
        
        # Mock translation check
        mock_translation.check_translation = AsyncMock(return_value=(True, "Correct", "Good!", 95))
        
        # Mock training service
        mock_training_service.update_session = AsyncMock()
        mock_training_service.update_daily_stats = AsyncMock()
        
        # Mock session
        mock_session_instance = AsyncMock()
        mock_session_instance.__aenter__ = AsyncMock(return_value=mock_session_instance)
        mock_session_instance.__aexit__ = AsyncMock(return_value=None)
        mock_session.return_value = mock_session_instance
        
        # Mock FSM context
        state = MagicMock(spec=FSMContext)
        state.set_state = AsyncMock()
        state.update_data = AsyncMock()
        
        # Call the handler
        await check_training_answer(message, state)
        
        # Verify training answer was processed
        mock_training_service.update_session.assert_called_once()
        mock_redis.clear_user_state.assert_called_once_with(12345)
        message.answer.assert_called_once()
    
    print("✓ Trainer handler processes answers correctly regardless of FSM state")


@pytest.mark.asyncio
async def test_translator_state_restored_after_training():
    """Test that translator state is restored after training answer is submitted."""
    from bot.handlers.trainer import check_training_answer
    
    # Mock message
    message = MagicMock(spec=Message)
    message.from_user = MagicMock(spec=User)
    message.from_user.id = 12345
    message.text = "My training answer"
    message.answer = AsyncMock()
    
    # Mock FSM context
    state = MagicMock(spec=FSMContext)
    state.set_state = AsyncMock()
    state.update_data = AsyncMock()
    
    # Mock Redis with active training session and saved translator state
    with patch('bot.services.redis_service.redis_service') as mock_redis, \
         patch('bot.handlers.trainer.async_session_maker') as mock_session, \
         patch('bot.handlers.trainer.mongo_service') as mock_mongo, \
         patch('bot.handlers.trainer.translation_service') as mock_translation, \
         patch('bot.handlers.trainer.UserService') as mock_user_service, \
         patch('bot.handlers.trainer.TrainingService') as mock_training_service:
        
        # Active training session in Redis
        mock_redis.get_user_state = AsyncMock(return_value={
            "state": "awaiting_training_answer",
            "data": {"training_id": "507f1f77bcf86cd799439011"}
        })
        mock_redis.clear_user_state = AsyncMock()
        
        # Saved translator state
        import json
        saved_state = json.dumps({
            "lang": "uk",
            "learning_lang": "en",
            "user_id": 1
        })
        mock_redis.get = AsyncMock(return_value=saved_state)
        mock_redis.set = AsyncMock()
        
        # Mock MongoDB training session
        from bson import ObjectId
        training_id = ObjectId("507f1f77bcf86cd799439011")
        mock_training_col = MagicMock()
        mock_training_col.find_one = AsyncMock(return_value={
            "_id": training_id,
            "sentence": "Test sentence",
            "expected_translation": "Тестове речення"
        })
        mock_mongo.db = MagicMock(return_value=MagicMock(
            training_sessions=mock_training_col
        ))
        
        # Mock user
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.interface_language.value = "uk"
        mock_user.learning_language.value = "en"
        mock_user.total_answers = 0
        mock_user.correct_answers = 0
        mock_user_service.get_or_create_user = AsyncMock(return_value=mock_user)
        mock_user_service.update_user = AsyncMock()
        mock_user_service.increment_activity = AsyncMock()
        
        # Mock translation check
        mock_translation.check_translation = AsyncMock(return_value=(True, "Correct", "Good!", 95))
        
        # Mock training service
        mock_training_service.update_session = AsyncMock()
        mock_training_service.update_daily_stats = AsyncMock()
        
        # Mock session
        mock_session_instance = AsyncMock()
        mock_session_instance.__aenter__ = AsyncMock(return_value=mock_session_instance)
        mock_session_instance.__aexit__ = AsyncMock(return_value=None)
        mock_session.return_value = mock_session_instance
        
        # Call the handler
        await check_training_answer(message, state)
        
        # Verify training answer was processed
        mock_training_service.update_session.assert_called_once()
        mock_redis.clear_user_state.assert_called_once_with(12345)
        message.answer.assert_called_once()
        
        # Verify saved state was retrieved (attempt to restore)
        mock_redis.get.assert_called()
    
    print("✓ Trainer processes answer and attempts to restore translator state")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
