"""
Tests for express trainer mode.
This test file validates the express trainer feature implementation.
"""
import pytest
import sys
import os

# Add bot directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bot'))


def test_express_trainer_handler_exists():
    """Test that express trainer handler module exists and has required functions."""
    # Check if the express_trainer.py file exists
    express_trainer_path = 'bot/handlers/express_trainer.py'
    assert os.path.exists(express_trainer_path), \
        "Express trainer handler should exist"
    
    with open(express_trainer_path, 'r') as f:
        content = f.read()
    
    # Check for key handler functions
    assert 'async def express_trainer_menu' in content, \
        "express_trainer_menu handler should exist"
    assert 'async def start_express_task' in content, \
        "start_express_task handler should exist"
    assert 'async def next_express_task' in content, \
        "next_express_task handler should exist"
    assert 'async def send_express_task' in content, \
        "send_express_task function should exist"
    assert 'async def check_express_answer' in content, \
        "check_express_answer handler should exist"
    assert 'async def show_express_settings' in content, \
        "show_express_settings handler should exist"
    
    print("✓ Express trainer handler has all required functions")


def test_express_trainer_localization():
    """Test that express trainer localization strings exist."""
    with open('bot/locales/texts.py', 'r') as f:
        content = f.read()
    
    # Check Ukrainian localization
    assert '"btn_express_trainer": "⚡️ Експрес тренажер"' in content, \
        "Ukrainian express trainer button text should exist"
    assert '"express_trainer_menu":' in content, \
        "Ukrainian express trainer menu text should exist"
    assert '"btn_get_next_sentence":' in content, \
        "Ukrainian get next sentence button text should exist"
    assert '"express_trainer_task":' in content, \
        "Ukrainian express trainer task text should exist"
    
    # Check Russian localization
    assert '"btn_express_trainer": "⚡️ Экспресс тренажёр"' in content, \
        "Russian express trainer button text should exist"
    
    print("✓ Express trainer localization strings are in place")


def test_express_trainer_keyboards():
    """Test that express trainer keyboard functions exist."""
    with open('bot/utils/keyboards.py', 'r') as f:
        content = f.read()
    
    # Check for keyboard functions
    assert 'def get_express_trainer_keyboard' in content, \
        "get_express_trainer_keyboard function should exist"
    assert 'def get_express_task_keyboard' in content, \
        "get_express_task_keyboard function should exist"
    assert 'def get_express_next_keyboard' in content, \
        "get_express_next_keyboard function should exist"
    assert 'def get_express_settings_keyboard' in content, \
        "get_express_settings_keyboard function should exist"
    assert 'def get_express_topic_level_keyboard' in content, \
        "get_express_topic_level_keyboard function should exist"
    assert 'def get_express_topic_selection_keyboard' in content, \
        "get_express_topic_selection_keyboard function should exist"
    
    print("✓ Express trainer keyboard functions exist")


def test_express_trainer_router_registration():
    """Test that express trainer router is registered in main.py."""
    with open('bot/main.py', 'r') as f:
        content = f.read()
    
    # Check that express_trainer is imported
    assert 'express_trainer' in content, \
        "express_trainer should be imported in main.py"
    
    # Check that router is included
    assert 'express_trainer.router' in content, \
        "express_trainer router should be registered"
    
    print("✓ Express trainer router is registered")


def test_express_trainer_topic_in_user_model():
    """Test that express_trainer_topic field exists in UserModel."""
    with open('bot/services/database_service.py', 'r') as f:
        content = f.read()
    
    # Check that express_trainer_topic is in UserModel
    assert 'self.express_trainer_topic' in content, \
        "express_trainer_topic field should exist in UserModel"
    
    # Check that it's included in to_update_dict
    assert '"express_trainer_topic": self.express_trainer_topic.value' in content, \
        "express_trainer_topic should be in to_update_dict"
    
    # Check that it's handled in update_user
    assert 'express_trainer_topic' in content and 'TrainerTopic' in content, \
        "express_trainer_topic should be handled in update_user"
    
    print("✓ express_trainer_topic field is properly integrated in UserModel")


def test_main_menu_includes_express_trainer():
    """Test that main menu keyboard includes express trainer button."""
    with open('bot/utils/keyboards.py', 'r') as f:
        content = f.read()
    
    # Check that express trainer button is added to main menu
    assert 'get_text(lang, "btn_express_trainer")' in content, \
        "Express trainer button should be in main menu"
    
    print("✓ Main menu includes express trainer button")


if __name__ == "__main__":
    test_express_trainer_handler_exists()
    test_express_trainer_localization()
    test_express_trainer_keyboards()
    test_express_trainer_router_registration()
    test_express_trainer_topic_in_user_model()
    test_main_menu_includes_express_trainer()
    print("\n✅ All express trainer tests passed!")
