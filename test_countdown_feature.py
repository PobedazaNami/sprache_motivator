"""
Test the countdown timer and progress tracking feature
"""
import pytest
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Add bot directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bot'))

from bot.services.scheduler_service import SchedulerService


@pytest.fixture
def scheduler():
    """Create scheduler service instance"""
    return SchedulerService()


@pytest.fixture
def mock_user():
    """Create a mock user object"""
    user = MagicMock()
    user.id = 123
    user.telegram_id = 456789
    user.trainer_start_time = "09:00"
    user.trainer_end_time = "21:00"
    user.trainer_messages_per_day = 3
    return user


@pytest.mark.asyncio
async def test_get_daily_progress_no_tasks(scheduler, mock_user):
    """Test getting daily progress when no tasks have been sent"""
    with patch('bot.services.redis_service.redis_service.get', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = None  # No tasks sent yet
        
        tasks_sent, total_tasks = await scheduler.get_daily_progress(mock_user)
        
        assert tasks_sent == 0
        assert total_tasks == 3


@pytest.mark.asyncio
async def test_get_daily_progress_some_tasks(scheduler, mock_user):
    """Test getting daily progress when some tasks have been sent"""
    with patch('bot.services.redis_service.redis_service.get', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = "2"  # 2 tasks sent
        
        tasks_sent, total_tasks = await scheduler.get_daily_progress(mock_user)
        
        assert tasks_sent == 2
        assert total_tasks == 3


@pytest.mark.asyncio
async def test_get_daily_progress_all_tasks(scheduler, mock_user):
    """Test getting daily progress when all tasks have been sent"""
    with patch('bot.services.redis_service.redis_service.get', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = "3"  # All 3 tasks sent
        
        tasks_sent, total_tasks = await scheduler.get_daily_progress(mock_user)
        
        assert tasks_sent == 3
        assert total_tasks == 3


@pytest.mark.asyncio
async def test_calculate_next_task_time_all_complete(scheduler, mock_user):
    """Test calculating next task time when all tasks for today are complete"""
    with patch('bot.services.redis_service.redis_service.get', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = "3"  # All tasks complete
        
        next_task_dt, countdown = await scheduler.calculate_next_task_time(mock_user)
        
        # Should return tomorrow's start time
        assert next_task_dt is not None
        assert "ч" in countdown or "мин" in countdown  # Should have hours or minutes
        
        # Verify it's tomorrow
        now_kyiv = datetime.now(ZoneInfo('Europe/Kyiv'))
        tomorrow = now_kyiv + timedelta(days=1)
        assert next_task_dt.date() == tomorrow.date()


@pytest.mark.asyncio
async def test_calculate_next_task_time_first_task(scheduler, mock_user):
    """Test calculating next task time when no tasks have been sent"""
    with patch('bot.services.redis_service.redis_service.get', new_callable=AsyncMock) as mock_get:
        # Mock Redis to return None for tasks sent and last slot
        async def mock_redis_get(key):
            return None
        
        mock_get.side_effect = mock_redis_get
        
        next_task_dt, countdown = await scheduler.calculate_next_task_time(mock_user)
        
        assert next_task_dt is not None
        assert countdown is not None
        # Countdown should be formatted as "Xч Yмин" or "Yмин"
        assert "мин" in countdown


@pytest.mark.asyncio
async def test_calculate_next_task_time_partial_progress(scheduler, mock_user):
    """Test calculating next task time when some tasks have been sent"""
    with patch('bot.services.redis_service.redis_service.get', new_callable=AsyncMock) as mock_get:
        # Mock Redis to return 1 task sent, last slot was 0
        async def mock_redis_get(key):
            if "tasks_today" in key:
                return "1"
            elif "last_slot" in key:
                return "0"
            return None
        
        mock_get.side_effect = mock_redis_get
        
        next_task_dt, countdown = await scheduler.calculate_next_task_time(mock_user)
        
        assert next_task_dt is not None
        assert countdown is not None
        assert "мин" in countdown


def test_time_diff_minutes(scheduler):
    """Test calculating time difference in minutes"""
    start = time(9, 0)
    end = time(21, 0)
    
    diff = scheduler._time_diff_minutes(start, end)
    
    assert diff == 720  # 12 hours = 720 minutes


def test_time_diff_minutes_same_time(scheduler):
    """Test calculating time difference when times are the same"""
    start = time(12, 0)
    end = time(12, 0)
    
    diff = scheduler._time_diff_minutes(start, end)
    
    assert diff == 0


def test_time_diff_minutes_short_window(scheduler):
    """Test calculating time difference for a short window"""
    start = time(9, 0)
    end = time(10, 30)
    
    diff = scheduler._time_diff_minutes(start, end)
    
    assert diff == 90  # 1.5 hours = 90 minutes


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
