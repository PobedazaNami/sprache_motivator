"""
Test to verify trainer settings update properly without refetching user data
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call


def test_trainer_no_redundant_fetches():
    """
    Verify that trainer.py doesn't have redundant get_or_create_user calls.
    This is a code inspection test to ensure the fix is in place.
    """
    # Read the trainer.py file
    with open('/home/runner/work/sprache_motivator/sprache_motivator/bot/handlers/trainer.py', 'r') as f:
        content = f.read()
    
    # Check that in set_time_period, there's only ONE call to get_or_create_user
    # Find the function boundaries more precisely
    set_time_period_start = content.find('async def set_time_period(callback: CallbackQuery):')
    # Find the next @router decorator after set_time_period
    next_router = content.find('@router.callback_query', set_time_period_start + 10)
    
    # Extract set_time_period function
    set_time_period_code = content[set_time_period_start:next_router]
    
    # Count occurrences of get_or_create_user in this function
    get_user_count = set_time_period_code.count('get_or_create_user')
    
    assert get_user_count == 1, f"set_time_period should call get_or_create_user only ONCE, found {get_user_count} calls"
    
    # Verify there's no "Fetch fresh user data" comment
    assert "Fetch fresh user data" not in set_time_period_code, "Redundant fetch comment still present"
    
    print("✓ set_time_period correctly uses updated user object without refetching")


def test_trainer_message_count_no_redundant_fetches():
    """
    Verify that set_message_count doesn't have redundant get_or_create_user calls.
    """
    # Read the trainer.py file
    with open('/home/runner/work/sprache_motivator/sprache_motivator/bot/handlers/trainer.py', 'r') as f:
        content = f.read()
    
    # Find the function boundaries
    set_message_count_start = content.find('async def set_message_count(callback: CallbackQuery):')
    # Find the next @router decorator after set_message_count
    next_router = content.find('@router.callback_query', set_message_count_start + 10)
    
    # Extract set_message_count function
    set_message_count_code = content[set_message_count_start:next_router]
    
    # Count occurrences of get_or_create_user in this function
    get_user_count = set_message_count_code.count('get_or_create_user')
    
    assert get_user_count == 1, f"set_message_count should call get_or_create_user only ONCE, found {get_user_count} calls"
    
    # Verify there's no "Fetch fresh user data" comment
    assert "Fetch fresh user data" not in set_message_count_code, "Redundant fetch comment still present"
    
    print("✓ set_message_count correctly uses updated user object without refetching")


def test_trainer_topic_no_redundant_fetches():
    """
    Verify that set_topic doesn't have redundant get_or_create_user calls.
    Note: set_topic has TWO code paths (random vs specific topic), each with its own 
    get_or_create_user call, but they never both execute (one returns early).
    """
    # Read the trainer.py file
    with open('/home/runner/work/sprache_motivator/sprache_motivator/bot/handlers/trainer.py', 'r') as f:
        content = f.read()
    
    # Find the function boundaries
    set_topic_start = content.find('async def set_topic(callback: CallbackQuery):')
    send_training_task_start = content.find('async def send_training_task(bot, user_id: int):')
    
    # Extract set_topic function
    set_topic_code = content[set_topic_start:send_training_task_start-1]
    
    # Count occurrences of get_or_create_user in this function
    get_user_count = set_topic_code.count('get_or_create_user')
    
    # set_topic has 2 branches, each with 1 call - that's correct
    assert get_user_count == 2, f"set_topic should have 2 get_or_create_user calls (one per branch), found {get_user_count} calls"
    
    # Verify there's no "Fetch fresh user data" comment (which indicates redundant refetch)
    assert "Fetch fresh user data" not in set_topic_code, "Redundant fetch comment still present"
    
    # Verify no redundant fetch WITHIN the same branch (should only be 1 per branch)
    # Check first branch (random topic with level)
    first_branch_start = set_topic_code.find("if topic_value.startswith")
    first_branch_end = set_topic_code.find("await callback.answer()\n        return")
    first_branch = set_topic_code[first_branch_start:first_branch_end]
    assert first_branch.count('get_or_create_user') == 1, "First branch should have only 1 get_or_create_user call"
    
    # Check second branch (specific topic)
    second_branch_start = set_topic_code.find("try:\n        topic = TrainerTopic")
    second_branch = set_topic_code[second_branch_start:]
    assert second_branch.count('get_or_create_user') == 1, "Second branch should have only 1 get_or_create_user call"
    
    print("✓ set_topic correctly uses updated user object without refetching in each branch")



if __name__ == "__main__":
    pytest.main([__file__, "-v"])
