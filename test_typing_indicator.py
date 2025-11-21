"""
Test for typing indicator functionality in trainer and translator modes.
This test validates that typing indicators are sent before processing user input.
"""
import pytest
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch

# Add bot directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bot'))


def test_trainer_has_typing_indicator():
    """Test that trainer.py includes send_chat_action call before translation check."""
    with open('bot/handlers/trainer.py', 'r') as f:
        content = f.read()
    
    # Check that typing indicator is present in check_training_answer function
    assert 'send_chat_action' in content, \
        "trainer.py should call send_chat_action for typing indicator"
    
    assert 'action="typing"' in content, \
        "trainer.py should use 'typing' action for chat action"
    
    # Verify it's before the check_translation call
    typing_pos = content.find('send_chat_action')
    check_translation_pos = content.find('check_translation')
    
    assert typing_pos < check_translation_pos, \
        "send_chat_action should be called before check_translation"
    
    print("✓ Trainer has typing indicator before translation check")


def test_translator_has_typing_indicator():
    """Test that translator.py includes send_chat_action call before translation."""
    with open('bot/handlers/translator.py', 'r') as f:
        content = f.read()
    
    # Check that typing indicator is present in process_translation function
    assert 'send_chat_action' in content, \
        "translator.py should call send_chat_action for typing indicator"
    
    assert 'action="typing"' in content, \
        "translator.py should use 'typing' action for chat action"
    
    # Verify it's in the process_translation function
    process_translation_start = content.find('async def process_translation')
    typing_pos = content.find('send_chat_action', process_translation_start)
    
    assert typing_pos > process_translation_start, \
        "send_chat_action should be in process_translation function"
    
    print("✓ Translator has typing indicator before translation")


def test_trainer_typing_indicator_location():
    """Test that typing indicator is placed correctly in trainer handler."""
    with open('bot/handlers/trainer.py', 'r') as f:
        lines = f.readlines()
    
    # Find the check_training_answer function
    in_check_function = False
    found_typing = False
    found_check_translation = False
    typing_line = -1
    check_line = -1
    
    for i, line in enumerate(lines):
        if 'async def check_training_answer' in line:
            in_check_function = True
        
        if in_check_function:
            if 'send_chat_action' in line and 'typing' in line:
                found_typing = True
                typing_line = i
            if 'check_translation' in line and 'translation_service' in line:
                found_check_translation = True
                check_line = i
                break
    
    assert found_typing, "Typing indicator should be in check_training_answer"
    assert found_check_translation, "check_translation call should be in function"
    assert typing_line < check_line, f"Typing indicator (line {typing_line}) should come before check_translation (line {check_line})"
    
    print(f"✓ Typing indicator correctly placed at line {typing_line}, before check_translation at line {check_line}")


def test_translator_typing_indicator_location():
    """Test that typing indicator is placed correctly in translator handler."""
    with open('bot/handlers/translator.py', 'r') as f:
        lines = f.readlines()
    
    # Find the process_translation function
    in_process_function = False
    found_typing = False
    found_translate = False
    typing_line = -1
    translate_line = -1
    
    for i, line in enumerate(lines):
        if 'async def process_translation' in line:
            in_process_function = True
        
        if in_process_function:
            if 'send_chat_action' in line and 'typing' in line:
                found_typing = True
                typing_line = i
            if 'translation_service.translate' in line:
                found_translate = True
                translate_line = i
                break
    
    assert found_typing, "Typing indicator should be in process_translation"
    assert found_translate, "translate call should be in function"
    assert typing_line < translate_line, f"Typing indicator (line {typing_line}) should come before translate (line {translate_line})"
    
    print(f"✓ Typing indicator correctly placed at line {typing_line}, before translate at line {translate_line}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
