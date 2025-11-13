"""
Test to verify the translation validation fix works correctly.
This test validates that invalid translations (like "Incorrect") are properly handled.
"""
import pytest
import sys
import os
from unittest.mock import AsyncMock, patch, MagicMock

# Add bot directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bot'))


def test_invalid_translation_detection():
    """Test that invalid translation words are detected."""
    with open('bot/services/translation_service.py', 'r') as f:
        content = f.read()
    
    # Check that invalid translation validation is in place
    assert "invalid_translation_words" in content, \
        "Code should check for invalid translation words"
    assert '"incorrect"' in content.lower() or "'incorrect'" in content.lower(), \
        "Should detect 'incorrect' as invalid translation"
    assert "await self.translate(" in content, \
        "Should have fallback to re-translate if invalid translation detected"
    
    print("✓ Invalid translation detection is in place")


def test_improved_prompt_quality_guidance():
    """Test that the prompt includes guidance for quality scoring."""
    with open('bot/services/translation_service.py', 'r') as f:
        content = f.read()
    
    # Check for improved quality scoring guidance
    assert "minor" in content.lower() and ("70-90" in content or "high quality" in content.lower()), \
        "Prompt should mention that minor errors should still get high quality scores"
    assert "0-30" in content or ("very low" in content.lower() and "completely wrong" in content.lower()), \
        "Prompt should specify when to give very low scores"
    
    print("✓ Quality scoring guidance is present in prompt")


def test_translation_field_clarity():
    """Test that the prompt is explicit about the TRANSLATION field."""
    with open('bot/services/translation_service.py', 'r') as f:
        content = f.read()
    
    # Check that prompt is explicit about translation field
    assert "MUST be an actual translation" in content or "must ALWAYS contain" in content.lower(), \
        "Prompt should be explicit that TRANSLATION must be actual translation"
    assert "NEVER words like" in content or 'not a status word' in content.lower(), \
        "Prompt should explicitly say not to use status words"
    
    print("✓ Translation field requirements are explicit in prompt")


@pytest.mark.asyncio
async def test_fallback_when_invalid_translation():
    """Test that the code falls back to re-translate when OpenAI returns invalid translation."""
    # Mock dependencies
    sys.modules['redis'] = MagicMock()
    sys.modules['redis.asyncio'] = MagicMock()
    
    from bot.services.translation_service import TranslationService
    
    # Mock OpenAI response with "Incorrect" as translation (the bug scenario)
    mock_check_response = MagicMock()
    mock_check_response.choices = [MagicMock()]
    mock_check_response.choices[0].message.content = """STATUS: INCORRECT
TRANSLATION: Incorrect
QUALITY: 10
EXPLANATION: Ваш переклад має помилки."""
    
    # Mock the fallback translate call response
    mock_translate_response = MagicMock()
    mock_translate_response.choices = [MagicMock()]
    mock_translate_response.choices[0].message.content = "Ich esse gerne Pizza"
    mock_translate_response.usage.total_tokens = 50
    
    with patch.object(TranslationService, '__init__', lambda self: None):
        service = TranslationService()
        service.client = MagicMock()
        service.client.chat = MagicMock()
        service.client.chat.completions = MagicMock()
        
        # First call returns the buggy response, second call (fallback) returns proper translation
        service.client.chat.completions.create = AsyncMock(side_effect=[
            mock_check_response,
            mock_translate_response
        ])
        
        # Mock redis_service for caching
        from bot.services.redis_service import redis_service
        redis_service.get_cached_translation = AsyncMock(return_value=None)
        redis_service.cache_translation = AsyncMock()
        redis_service.get_user_tokens_today = AsyncMock(return_value=0)
        redis_service.increment_user_tokens = AsyncMock()
        
        is_correct, correct_translation, explanation, quality = await service.check_translation(
            original="Я люблю їсти піцу",
            user_translation="ich esse gern Pizza",
            expected_lang="de",
            interface_lang="uk"
        )
        
        # Verify the fallback was triggered and got proper translation
        assert correct_translation != "Incorrect", \
            "Should not show 'Incorrect' as the correct translation"
        assert "Pizza" in correct_translation or "pizza" in correct_translation.lower(), \
            f"Should contain actual German translation, got: {correct_translation}"
        assert is_correct == False, "Should still mark as incorrect due to minor errors"
        
        print(f"✓ Fallback works correctly: got '{correct_translation}' instead of 'Incorrect'")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
