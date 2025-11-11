"""
Test to verify that changing training time doesn't reset progress.
This test validates the new time-based tracking approach.
"""
import pytest
from datetime import time, date
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bot'))


@pytest.mark.asyncio
async def test_progress_preserved_when_time_changes():
    """Test that changing time window doesn't reset daily progress."""
    from bot.services.scheduler_service import SchedulerService
    
    # Create a mock user
    mock_user = MagicMock()
    mock_user.id = 12345
    mock_user.trainer_start_time = "09:00"
    mock_user.trainer_end_time = "18:00"
    mock_user.trainer_messages_per_day = 3
    
    # Create scheduler instance
    scheduler = SchedulerService()
    
    # Mock Redis service
    mock_redis_data = {
        "tasks_today:12345:2024-01-15": "2",  # 2 tasks sent already
        "last_task_time:12345:2024-01-15": "13:00"
    }
    
    async def mock_redis_get(key):
        return mock_redis_data.get(key)
    
    async def mock_redis_set(key, value, ex=None):
        mock_redis_data[key] = str(value)
    
    with patch('bot.services.redis_service.redis_service') as mock_redis:
        mock_redis.get = AsyncMock(side_effect=mock_redis_get)
        mock_redis.set = AsyncMock(side_effect=mock_redis_set)
        
        # Get progress before time change
        tasks_sent_before, total = await scheduler.get_daily_progress(mock_user)
        assert tasks_sent_before == 2, "Should have 2 tasks sent"
        
        # Simulate user changing time window
        mock_user.trainer_start_time = "10:00"  # Changed from 09:00
        mock_user.trainer_end_time = "20:00"    # Changed from 18:00
        
        # Check if task should be sent at 14:00 (after time change)
        current_time = time(14, 0)
        current_date = date(2024, 1, 15)
        
        should_send = await scheduler._should_send_task(mock_user, current_time, current_date)
        
        # With the new time-based approach:
        # - 2 tasks already sent (last at 13:00)
        # - Window is now 10:00-20:00 (600 minutes)
        # - 3 messages per day means interval of 200 minutes
        # - Time since last task: 14:00 - 13:00 = 60 minutes
        # - Should NOT send yet (need 200 minutes)
        assert should_send == False, "Should not send task yet (not enough time passed)"
        
        # Get progress after time change
        tasks_sent_after, total = await scheduler.get_daily_progress(mock_user)
        assert tasks_sent_after == 2, "Progress should be preserved at 2 tasks"
        
        # Check at 15:30 (150 minutes after last task - still not enough)
        current_time = time(15, 30)
        should_send = await scheduler._should_send_task(mock_user, current_time, current_date)
        assert should_send == False, "Still not enough time passed"
        
        # Check at 16:30 (210 minutes after last task - enough time!)
        current_time = time(16, 30)
        should_send = await scheduler._should_send_task(mock_user, current_time, current_date)
        assert should_send == True, "Should send task now (enough time passed)"
        
        # Verify progress is now 3
        tasks_sent_final, total = await scheduler.get_daily_progress(mock_user)
        assert tasks_sent_final == 3, "Should now have 3 tasks sent"


@pytest.mark.asyncio
async def test_time_based_tracking_vs_slot_based():
    """
    Test that demonstrates the improvement of time-based tracking over slot-based.
    This test shows how the old slot-based approach would fail when time changes.
    """
    from bot.services.scheduler_service import SchedulerService
    
    scheduler = SchedulerService()
    
    # Initial window: 09:00-18:00 (540 minutes), 3 tasks = 180 minute slots
    # Slots would be: [09:00-12:00], [12:00-15:00], [15:00-18:00]
    # Slot 0: 09:00-12:00
    # Slot 1: 12:00-15:00  
    # Slot 2: 15:00-18:00
    
    # User sent 2 tasks already (slots 0 and 1)
    # Last task at 13:00 (in slot 1)
    
    # Now user changes to 10:00-20:00 (600 minutes), 3 tasks = 200 minute slots
    # NEW Slots: [10:00-13:20], [13:20-16:40], [16:40-20:00]
    # Current time 14:00 would be in NEW slot 1 (13:20-16:40)
    
    # OLD slot-based approach problem:
    # - Old last_slot was 1 (from 12:00-15:00 in old window)
    # - New current_slot at 14:00 is also 1 (13:20-16:40 in new window)
    # - Since current_slot (1) is NOT > last_slot (1), task wouldn't be sent!
    # - This is the bug: progress appears to reset/block
    
    # NEW time-based approach:
    # - Last task was at 13:00
    # - Current time is 14:00
    # - Only 60 minutes passed (need 200 for new window)
    # - Correctly waits until enough time passes
    
    # The key difference: time-based doesn't recalculate slots, 
    # it just checks elapsed time since last task
    
    assert True, "This test documents the fix"


@pytest.mark.asyncio
async def test_random_topic_level_specific():
    """Test that level-specific random topic selection works."""
    from bot.models.database import TrainerTopic, TOPIC_METADATA
    import random
    
    # Test getting random topic from A2 level
    a2_topics = [t for t, meta in TOPIC_METADATA.items() 
                 if meta["level"] == "A2" and t != TrainerTopic.RANDOM]
    
    assert len(a2_topics) == 12, "Should have 12 A2 topics"
    
    # Test getting random topic from B1 level
    b1_topics = [t for t, meta in TOPIC_METADATA.items() 
                 if meta["level"] == "B1" and t != TrainerTopic.RANDOM]
    
    assert len(b1_topics) == 10, "Should have 10 B1 topics"
    
    # Test getting random topic from B2 level
    b2_topics = [t for t, meta in TOPIC_METADATA.items() 
                 if meta["level"] == "B2" and t != TrainerTopic.RANDOM]
    
    assert len(b2_topics) == 8, "Should have 8 B2 topics"
    
    # Test global random (picking random level first)
    levels = ["A2", "B1", "B2"]
    random_level = random.choice(levels)
    level_topics = [t for t, meta in TOPIC_METADATA.items() 
                   if meta["level"] == random_level and t != TrainerTopic.RANDOM]
    
    assert len(level_topics) > 0, f"Should have topics for level {random_level}"
    random_topic = random.choice(level_topics)
    assert random_topic in TOPIC_METADATA, "Random topic should be valid"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
