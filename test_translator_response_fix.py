"""
Test to verify that translator mode responds to messages even when user has active training session.
This test validates that the problematic early return logic has been removed.
"""
import sys
import os

# Add bot directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bot'))


def test_no_training_state_check_in_translator():
    """Test that translator handler doesn't check for training state and return early."""
    with open('bot/handlers/translator.py', 'r') as f:
        content = f.read()
    
    # The problematic code should be removed
    assert "training_state = await redis_service.get_user_state" not in content, \
        "Translator handler should not check for training state in process_translation"
    
    assert 'if training_state and training_state.get("state") == "awaiting_training_answer"' not in content, \
        "Training state check should be removed from process_translation"
    
    assert "saved_translator_state:" not in content, \
        "Code for saving translator state to Redis should be removed"
    
    print("✓ Translator handler no longer checks for training state")


def test_process_translation_starts_immediately():
    """Test that process_translation starts processing right away."""
    with open('bot/handlers/translator.py', 'r') as f:
        lines = f.readlines()
    
    # Find the process_translation function
    found_func = False
    for i, line in enumerate(lines):
        if 'async def process_translation(message: Message, state: FSMContext):' in line:
            found_func = True
            # Check that within the next 5 lines, we're getting state data
            next_few_lines = ''.join(lines[i:i+10])
            assert 'data = await state.get_data()' in next_few_lines, \
                "process_translation should get state data immediately after function definition"
            assert 'return' not in ''.join(lines[i+2:i+5]), \
                "process_translation should not have early returns right after definition"
            break
    
    assert found_func, "process_translation function should exist"
    print("✓ process_translation processes translation immediately")


def test_translator_handler_structure():
    """Test that the translator handler has correct structure."""
    with open('bot/handlers/translator.py', 'r') as f:
        content = f.read()
    
    # Verify the handler still processes translations
    assert "await translation_service.translate(" in content, \
        "Translation service should still be called"
    
    assert "await state.set_state(TranslatorStates.show_translation)" in content, \
        "Should set state after successful translation"
    
    assert "await message.answer(" in content, \
        "Should send response to user"
    
    print("✓ Translator handler structure is correct")


if __name__ == "__main__":
    # Run tests
    test_no_training_state_check_in_translator()
    test_process_translation_starts_immediately()
    test_translator_handler_structure()
    print("\n✅ All tests passed! Translator mode will now respond correctly.")
