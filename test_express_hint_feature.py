"""
Test for hint button functionality in express trainer.
This test verifies that the hint button works correctly in the express trainer mode.
"""
import sys
import os

# Add bot directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bot'))


def test_hint_handler_exists_in_express_trainer():
    """Test that hint handler exists in express trainer."""
    with open('bot/handlers/express_trainer.py', 'r') as f:
        content = f.read()
    
    # Check that hint handler is defined
    assert 'async def show_hint' in content, \
        "show_hint handler should exist in express trainer"
    
    # Check that it's registered as a callback handler
    assert '@router.callback_query(F.data.startswith("hint_"))' in content, \
        "Hint callback handler should be registered"
    
    # Check that it clears user state
    assert 'await redis_service.clear_user_state' in content, \
        "Handler should clear user state after showing hint"
    
    # Check that it tracks hint activation
    assert 'await mongo_service.track_hint_activation' in content, \
        "Handler should track hint activation"
    
    print("✓ Hint handler exists in express trainer")


def test_hint_button_in_express_task_keyboard():
    """Test that hint button is included in express task keyboard."""
    with open('bot/utils/keyboards.py', 'r') as f:
        content = f.read()
    
    # Check that express task keyboard includes hint button
    assert 'def get_express_task_keyboard' in content, \
        "get_express_task_keyboard function should exist"
    
    # Extract the function to check it includes hint button
    lines = content.split('\n')
    in_function = False
    function_content = []
    
    for line in lines:
        if 'def get_express_task_keyboard' in line:
            in_function = True
        elif in_function:
            if line.strip().startswith('def '):
                break
            function_content.append(line)
    
    function_text = '\n'.join(function_content)
    assert 'btn_get_hint' in function_text, \
        "Express task keyboard should include hint button"
    assert 'hint_' in function_text, \
        "Hint button should use hint_ callback data prefix"
    
    print("✓ Hint button is included in express task keyboard")


def test_hint_localization_texts_exist():
    """Test that hint localization texts exist."""
    with open('bot/locales/texts.py', 'r') as f:
        content = f.read()
    
    # Check that hint button text exists
    assert '"btn_get_hint":' in content, \
        "Hint button text should exist in localization"
    
    # Check that hint activated message exists
    assert '"hint_activated":' in content, \
        "Hint activated message should exist in localization"
    
    print("✓ Hint localization texts exist")


def test_express_trainer_hint_workflow():
    """Test the complete hint workflow in express trainer."""
    with open('bot/handlers/express_trainer.py', 'r') as f:
        content = f.read()
    
    # Verify the workflow steps are present:
    # 1. Extract training ID from callback
    assert 'training_id_str = callback.data.replace("hint_", "")' in content, \
        "Handler should extract training ID from callback"
    
    # 2. Convert to ObjectId
    assert 'ObjectId(training_id_str)' in content, \
        "Handler should convert training ID to ObjectId"
    
    # 3. Fetch training session from MongoDB
    assert 'training = await training_col.find_one({"_id": training_id})' in content, \
        "Handler should fetch training session from MongoDB"
    
    # 4. Get expected translation
    assert 'expected_translation = training.get("expected_translation", "")' in content, \
        "Handler should get expected translation"
    
    # 5. Remove keyboard to prevent multiple clicks
    assert 'await callback.message.edit_reply_markup(reply_markup=None)' in content, \
        "Handler should remove keyboard from original message"
    
    # 6. Show hint message
    assert 'get_text(lang, "hint_activated", translation=expected_translation)' in content, \
        "Handler should show hint with translation"
    
    # 7. Track hint activation
    assert 'await mongo_service.track_hint_activation(user.id)' in content, \
        "Handler should track hint activation"
    
    # 8. Clear user state
    assert 'await redis_service.clear_user_state(callback.from_user.id)' in content, \
        "Handler should clear user state"
    
    print("✓ Complete hint workflow is implemented correctly")


def test_no_duplicate_hint_handlers():
    """Test that hint handler is not duplicated (one per trainer type is expected)."""
    with open('bot/handlers/express_trainer.py', 'r') as f:
        express_content = f.read()
    
    # Count hint handlers in express trainer
    express_hint_count = express_content.count('async def show_hint')
    assert express_hint_count == 1, \
        f"Express trainer should have exactly 1 hint handler, found {express_hint_count}"
    
    print("✓ No duplicate hint handlers found")


if __name__ == "__main__":
    test_hint_handler_exists_in_express_trainer()
    test_hint_button_in_express_task_keyboard()
    test_hint_localization_texts_exist()
    test_express_trainer_hint_workflow()
    test_no_duplicate_hint_handlers()
    print("\n✅ All express trainer hint feature tests passed!")
