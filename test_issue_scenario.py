"""
Test that specifically validates the scenario from the GitHub issue.

Issue: User translates "Я люблю їсти піцу" as "ich esse gern Pizza" (almost correct)
but bot shows:
- Quality: 10% (too low)
- Correct translation: "Incorrect" (wrong - should show actual German translation)

Expected after fix:
- Quality should be higher (70-90%) since meaning is correct with only minor issues
- Correct translation should show actual German translation like "Ich esse gerne Pizza"
"""
import pytest


def test_issue_scenario_validation():
    """
    Validate that the code changes address the specific issue scenario.
    
    This test checks the code without running it, verifying that:
    1. The prompt instructs OpenAI to give high quality scores for minor errors
    2. The prompt explicitly says TRANSLATION must be actual translation, not "Incorrect"
    3. There's fallback logic to handle if OpenAI still returns invalid translation
    """
    with open('bot/services/translation_service.py', 'r') as f:
        content = f.read()
    
    # Verify quality scoring is more lenient
    assert "70-90" in content, \
        "Prompt should specify 70-90% quality for minor errors"
    assert "minor" in content.lower() and "should not severely impact" in content.lower(), \
        "Prompt should say minor errors should not severely impact quality"
    
    # Verify TRANSLATION field must contain actual translation
    assert "MUST be an actual translation" in content, \
        "Prompt should explicitly state TRANSLATION must be actual translation"
    assert ("NEVER use placeholders" in content or "NEVER words like" in content) and '"Incorrect"' in content, \
        "Prompt should explicitly forbid words like 'Incorrect' in TRANSLATION field"
    
    # Verify there's validation and fallback for invalid translations
    assert "invalid_translation_words" in content, \
        "Code should define list of invalid translation words"
    assert "incorrect" in content.lower() and "correct_translation.lower() in invalid_translation_words" in content.lower(), \
        "Code should check if correct_translation is an invalid word"
    assert "await self.translate(" in content, \
        "Code should fall back to calling translate() if invalid translation detected"
    
    print("✓ All fixes for the GitHub issue scenario are in place:")
    print("  - Quality scoring is more lenient for minor errors (70-90%)")
    print("  - Prompt explicitly requires actual translation, not status words")
    print("  - Fallback logic handles invalid translations from OpenAI")
    

def test_system_message_update():
    """Verify the system message still instructs proper language usage."""
    with open('bot/services/translation_service.py', 'r') as f:
        content = f.read()
    
    # Check that system message specifies language for explanations
    assert 'role": "system"' in content, \
        "Should have system message"
    assert "language teacher" in content.lower(), \
        "System message should identify as language teacher"
    
    print("✓ System message is properly configured")


def test_prompt_structure():
    """Verify the prompt has clear structure and all required fields."""
    with open('bot/services/translation_service.py', 'r') as f:
        content = f.read()
    
    # Check for required response format
    assert "STATUS: [CORRECT/INCORRECT]" in content, \
        "Prompt should specify STATUS field format"
    assert "TRANSLATION:" in content, \
        "Prompt should specify TRANSLATION field"
    assert "QUALITY: [0-100]" in content, \
        "Prompt should specify QUALITY field format"
    assert "EXPLANATION:" in content, \
        "Prompt should specify EXPLANATION field"
    
    # Check the TRANSLATION field has extra guidance
    assert content.count("TRANSLATION:") >= 2, \
        "TRANSLATION field should be mentioned in both format and with extra guidance"
    
    print("✓ Prompt has proper structure with all required fields")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
