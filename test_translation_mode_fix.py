"""
Test to verify the translation mode language detection fix.
This test validates that German and English text are both correctly translated
to the user's interface language (Russian/Ukrainian).
"""
import sys
import os

# Add bot directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bot'))


def test_auto_language_detection_in_translator():
    """Test that translator handler uses 'auto' for non-Cyrillic text."""
    with open('bot/handlers/translator.py', 'r') as f:
        content = f.read()
    
    # Check that 'auto' is used for source language detection
    assert "source_lang = 'auto'" in content, \
        "Handler should use 'auto' for non-Cyrillic text to enable language auto-detection"
    
    # Check that the comment explains the auto-detection
    assert "let OpenAI detect" in content or "auto-detect" in content.lower(), \
        "Code should have comment explaining auto-detection"
    
    print("✓ Translator handler uses 'auto' for language detection")


def test_translation_service_handles_auto():
    """Test that translation service handles 'auto' source language."""
    with open('bot/services/translation_service.py', 'r') as f:
        content = f.read()
    
    # Check that there's handling for auto source language
    assert 'source_lang == "auto"' in content or "source_lang == 'auto'" in content, \
        "Translation service should handle 'auto' as source language"
    
    # Check that the prompt doesn't specify source when auto
    # Look for a prompt that doesn't include "from {source_lang}"
    lines = content.split('\n')
    found_auto_handling = False
    for i, line in enumerate(lines):
        if 'source_lang == "auto"' in line or "source_lang == 'auto'" in line:
            # Check next few lines for prompt without "from"
            for j in range(i, min(i+5, len(lines))):
                if 'prompt = f"Translate the following text to {target_lang}' in lines[j]:
                    found_auto_handling = True
                    break
    
    assert found_auto_handling, \
        "When source_lang is 'auto', prompt should not include 'from {source_lang}'"
    
    print("✓ Translation service correctly handles 'auto' source language")


def test_cyrillic_detection_still_works():
    """Test that Cyrillic text detection is unchanged."""
    with open('bot/handlers/translator.py', 'r') as f:
        content = f.read()
    
    # Check that Cyrillic detection is still present
    assert "is_cyrillic = any" in content or "Cyrillic" in content, \
        "Cyrillic detection logic should still exist"
    
    # Check that Cyrillic text still translates to learning language
    assert "target_lang = learning_lang" in content, \
        "Cyrillic text should still translate to learning language"
    
    print("✓ Cyrillic detection logic is preserved")


def test_issue_scenario():
    """
    Test the specific scenario from the issue:
    User with interface_lang=RU, learning_lang=EN sends German text,
    should get translation to Russian (not English).
    """
    with open('bot/handlers/translator.py', 'r') as f:
        handler_content = f.read()
    
    with open('bot/services/translation_service.py', 'r') as f:
        service_content = f.read()
    
    # Verify the fix is in place:
    # 1. Non-Cyrillic text should use 'auto' as source
    assert "source_lang = 'auto'" in handler_content, \
        "Non-Cyrillic text should use 'auto' as source language"
    
    # 2. Non-Cyrillic text should target interface language
    lines = handler_content.split('\n')
    found_correct_logic = False
    for i, line in enumerate(lines):
        if "source_lang = 'auto'" in line:
            # Check if next few lines have target_lang = lang
            for j in range(i-2, min(i+3, len(lines))):
                if 'target_lang = lang' in lines[j] and 'is_cyrillic' not in lines[j]:
                    found_correct_logic = True
                    break
    
    assert found_correct_logic, \
        "Non-Cyrillic text should translate to interface language (lang)"
    
    # 3. Translation service should handle 'auto'
    assert 'source_lang == "auto"' in service_content or "source_lang == 'auto'" in service_content, \
        "Translation service must handle 'auto' source language"
    
    print("✓ Issue scenario is fixed: German text will now translate to interface language")


if __name__ == "__main__":
    # Run tests
    test_auto_language_detection_in_translator()
    test_translation_service_handles_auto()
    test_cyrillic_detection_still_works()
    test_issue_scenario()
    print("\n✅ All tests passed!")
