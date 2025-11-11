"""
Test to verify that progress display updates correctly after settings changes.
"""
import pytest
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bot'))


@pytest.mark.asyncio
async def test_progress_updates_after_count_change():
    """Test that progress display updates when message count is changed."""
    from bot.services.scheduler_service import SchedulerService
    
    # Create a mock user
    mock_user = MagicMock()
    mock_user.id = 12345
    mock_user.trainer_start_time = "09:00"
    mock_user.trainer_end_time = "18:00"
    mock_user.trainer_messages_per_day = 8  # Initially 8
    mock_user.daily_trainer_enabled = True
    
    # Create scheduler instance
    scheduler = SchedulerService()
    
    # Mock Redis service
    mock_redis_data = {
        "tasks_today:12345:" + str(date.today()): "8",  # 8 tasks sent
    }
    
    async def mock_redis_get(key):
        return mock_redis_data.get(key)
    
    with patch('bot.services.redis_service.redis_service') as mock_redis:
        mock_redis.get = AsyncMock(side_effect=mock_redis_get)
        
        # Get progress with 8 messages per day setting
        tasks_sent, total = await scheduler.get_daily_progress(mock_user)
        assert tasks_sent == 8, "Should have 8 tasks sent"
        assert total == 8, "Total should be 8"
        
        # User changes to 7 messages per day
        mock_user.trainer_messages_per_day = 7
        
        # Get progress with new setting
        tasks_sent, total = await scheduler.get_daily_progress(mock_user)
        assert tasks_sent == 8, "Tasks sent should still be 8 (not reset)"
        assert total == 7, "Total should now be 7 (updated)"


@pytest.mark.asyncio
async def test_progress_updates_after_time_change():
    """Test that progress display updates when time period is changed."""
    from bot.services.scheduler_service import SchedulerService
    
    # Create a mock user
    mock_user = MagicMock()
    mock_user.id = 12345
    mock_user.trainer_start_time = "09:00"
    mock_user.trainer_end_time = "18:00"
    mock_user.trainer_messages_per_day = 5
    mock_user.daily_trainer_enabled = True
    
    # Create scheduler instance
    scheduler = SchedulerService()
    
    # Mock Redis service
    mock_redis_data = {
        "tasks_today:12345:" + str(date.today()): "3",  # 3 tasks sent
    }
    
    async def mock_redis_get(key):
        return mock_redis_data.get(key)
    
    with patch('bot.services.redis_service.redis_service') as mock_redis:
        mock_redis.get = AsyncMock(side_effect=mock_redis_get)
        
        # Get progress before time change
        tasks_sent, total = await scheduler.get_daily_progress(mock_user)
        assert tasks_sent == 3, "Should have 3 tasks sent"
        assert total == 5, "Total should be 5"
        
        # User changes time period (this doesn't affect total, but we verify it doesn't break)
        mock_user.trainer_start_time = "10:00"
        mock_user.trainer_end_time = "20:00"
        
        # Get progress after time change
        tasks_sent, total = await scheduler.get_daily_progress(mock_user)
        assert tasks_sent == 3, "Tasks sent should still be 3 (not reset)"
        assert total == 5, "Total should still be 5"


@pytest.mark.asyncio
async def test_progress_not_reset_only_total_updates():
    """Test that changing settings doesn't reset the sent count, only updates total."""
    from bot.services.scheduler_service import SchedulerService
    
    # Create a mock user
    mock_user = MagicMock()
    mock_user.id = 12345
    mock_user.trainer_start_time = "09:00"
    mock_user.trainer_end_time = "18:00"
    mock_user.trainer_messages_per_day = 10
    mock_user.daily_trainer_enabled = True
    
    # Create scheduler instance
    scheduler = SchedulerService()
    
    # Mock Redis service - user has completed 10 tasks
    mock_redis_data = {
        "tasks_today:12345:" + str(date.today()): "10",  # 10 tasks sent
    }
    
    async def mock_redis_get(key):
        return mock_redis_data.get(key)
    
    with patch('bot.services.redis_service.redis_service') as mock_redis:
        mock_redis.get = AsyncMock(side_effect=mock_redis_get)
        
        # Get progress with 10 messages per day
        tasks_sent, total = await scheduler.get_daily_progress(mock_user)
        assert tasks_sent == 10, "Should have 10 tasks sent"
        assert total == 10, "Total should be 10"
        
        # User reduces to 5 messages per day
        mock_user.trainer_messages_per_day = 5
        
        # Get progress - should show 10/5 (exceeded)
        tasks_sent, total = await scheduler.get_daily_progress(mock_user)
        assert tasks_sent == 10, "Tasks sent should still be 10"
        assert total == 5, "Total should now be 5"
        # This is expected: user exceeded their new daily limit


@pytest.mark.asyncio
async def test_settings_keyboard_no_difficulty():
    """Test that settings keyboard doesn't include difficulty level."""
    from bot.utils.keyboards import get_settings_keyboard
    
    # Get settings keyboard for Ukrainian
    keyboard_uk = get_settings_keyboard("uk")
    
    # Convert keyboard to dict to inspect
    keyboard_dict = keyboard_uk.dict() if hasattr(keyboard_uk, 'dict') else keyboard_uk.model_dump()
    
    # Check that there's no difficulty button
    buttons = []
    for row in keyboard_dict.get('inline_keyboard', []):
        for button in row:
            buttons.append(button.get('callback_data', ''))
    
    assert 'settings_difficulty' not in buttons, "Difficulty button should not be in settings keyboard"
    assert 'settings_interface_lang' in buttons, "Interface language button should be present"
    assert 'settings_learning_lang' in buttons, "Learning language button should be present"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
