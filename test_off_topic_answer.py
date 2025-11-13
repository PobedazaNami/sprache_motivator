"""
Test that validates the specific issue scenario where user provides an off-topic answer.

Issue: User translates a sentence with "Vielen Leuten" (completely off-topic)
and bot shows:
- Correct translation: "N/A" (wrong - should show actual translation)
- Generic explanation that doesn't help the user learn

Expected after fix:
- Correct translation should ALWAYS show actual translation, even for off-topic answers
- Explanation should be helpful
"""
import pytest
import sys
import os
from unittest.mock import AsyncMock, patch, MagicMock

# Add bot directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bot'))


@pytest.mark.asyncio
async def test_off_topic_answer_gets_correct_translation():
    """Test that off-topic answers still receive the correct translation."""
    sys.modules['redis'] = MagicMock()
    sys.modules['redis.asyncio'] = MagicMock()
    
    from bot.services.translation_service import TranslationService
    
    # Mock OpenAI response where it returns "N/A" in the TRANSLATION field
    # This simulates the bug scenario
    mock_check_response = MagicMock()
    mock_check_response.choices = [MagicMock()]
    mock_check_response.choices[0].message.content = """STATUS: INCORRECT
TRANSLATION: N/A
QUALITY: 10
EXPLANATION: Переклад користувача "Vielen Leuten" не є спробою перекладу оригінального речення. Він є некоректним і не має відношення до заданого тексту."""
    
    # Mock the fallback translation call
    mock_translate_response = MagicMock()
    mock_translate_response.choices = [MagicMock()]
    mock_translate_response.choices[0].message.content = "Ich liebe es, Pizza zu essen."
    mock_translate_response.usage.total_tokens = 50
    
    with patch.object(TranslationService, '__init__', lambda self: None):
        service = TranslationService()
        service.client = MagicMock()
        service.client.chat = MagicMock()
        service.client.chat.completions = MagicMock()
        
        # Mock the translate method to return proper translation
        async def mock_translate(text, source_lang, target_lang, user_id=None):
            return "Ich liebe es, Pizza zu essen.", 50
        
        service.translate = AsyncMock(side_effect=mock_translate)
        
        # Set up the mock to return the check response
        service.client.chat.completions.create = AsyncMock(return_value=mock_check_response)
        
        is_correct, correct_translation, explanation, quality = await service.check_translation(
            original="Я люблю їсти піцу",
            user_translation="Vielen Leuten",
            expected_lang="de",
            interface_lang="uk"
        )
        
        # Validate the results
        assert is_correct == False, "Off-topic answer should be marked incorrect"
        assert quality <= 20, f"Off-topic answer should have very low quality (<= 20%), got {quality}%"
        
        # The critical assertion - correct_translation should NEVER be "N/A" or empty
        assert correct_translation != "N/A", "Correct translation should never be 'N/A'"
        assert correct_translation != "", "Correct translation should never be empty"
        assert len(correct_translation) > 3, "Correct translation should be a real translation"
        
        # It should contain German words (the actual translation)
        assert any(word in correct_translation for word in ["Ich", "liebe", "Pizza", "essen"]), \
            f"Correct translation should be actual German translation, got: {correct_translation}"
        
        print(f"✓ Off-topic answer correctly returns actual translation: {correct_translation}")


@pytest.mark.asyncio
async def test_empty_translation_field_gets_fallback():
    """Test that empty TRANSLATION field triggers fallback."""
    sys.modules['redis'] = MagicMock()
    sys.modules['redis.asyncio'] = MagicMock()
    
    from bot.services.translation_service import TranslationService
    
    # Mock OpenAI response where TRANSLATION field is empty
    mock_check_response = MagicMock()
    mock_check_response.choices = [MagicMock()]
    mock_check_response.choices[0].message.content = """STATUS: INCORRECT
TRANSLATION: 
QUALITY: 5
EXPLANATION: Відповідь користувача не має відношення до оригінального речення."""
    
    # Mock the fallback translation call
    mock_translate_response = MagicMock()
    mock_translate_response.choices = [MagicMock()]
    mock_translate_response.choices[0].message.content = "Der Hund läuft schnell."
    mock_translate_response.usage.total_tokens = 30
    
    with patch.object(TranslationService, '__init__', lambda self: None):
        service = TranslationService()
        service.client = MagicMock()
        service.client.chat = MagicMock()
        service.client.chat.completions = MagicMock()
        
        # Mock the translate method to return proper translation
        async def mock_translate(text, source_lang, target_lang, user_id=None):
            return "Der Hund läuft schnell.", 30
        
        service.translate = AsyncMock(side_effect=mock_translate)
        
        service.client.chat.completions.create = AsyncMock(return_value=mock_check_response)
        
        is_correct, correct_translation, explanation, quality = await service.check_translation(
            original="Собака швидко біжить",
            user_translation="random words",
            expected_lang="de",
            interface_lang="uk"
        )
        
        # Validate that fallback worked
        assert correct_translation != "", "Empty translation should trigger fallback"
        assert len(correct_translation) > 5, "Should have real translation after fallback"
        assert "Hund" in correct_translation or "läuft" in correct_translation, \
            f"Should contain actual German translation, got: {correct_translation}"
        
        print(f"✓ Empty translation field correctly triggers fallback: {correct_translation}")


@pytest.mark.asyncio  
async def test_dash_translation_field_gets_fallback():
    """Test that dash in TRANSLATION field triggers fallback."""
    sys.modules['redis'] = MagicMock()
    sys.modules['redis.asyncio'] = MagicMock()
    
    from bot.services.translation_service import TranslationService
    
    # Mock OpenAI response where TRANSLATION field is a dash
    mock_check_response = MagicMock()
    mock_check_response.choices = [MagicMock()]
    mock_check_response.choices[0].message.content = """STATUS: INCORRECT
TRANSLATION: -
QUALITY: 8
EXPLANATION: Відповідь не є перекладом."""
    
    # Mock the fallback translation call
    mock_translate_response = MagicMock()
    mock_translate_response.choices = [MagicMock()]
    mock_translate_response.choices[0].message.content = "Ich gehe zur Schule."
    mock_translate_response.usage.total_tokens = 25
    
    with patch.object(TranslationService, '__init__', lambda self: None):
        service = TranslationService()
        service.client = MagicMock()
        service.client.chat = MagicMock()
        service.client.chat.completions = MagicMock()
        
        # Mock the translate method to return proper translation
        async def mock_translate(text, source_lang, target_lang, user_id=None):
            return "Ich gehe zur Schule.", 25
        
        service.translate = AsyncMock(side_effect=mock_translate)
        
        service.client.chat.completions.create = AsyncMock(return_value=mock_check_response)
        
        is_correct, correct_translation, explanation, quality = await service.check_translation(
            original="Я йду до школи",
            user_translation="xyz",
            expected_lang="de",
            interface_lang="uk"
        )
        
        # Validate that fallback worked
        assert correct_translation != "-", "Dash translation should trigger fallback"
        assert len(correct_translation) > 5, "Should have real translation after fallback"
        
        print(f"✓ Dash in translation field correctly triggers fallback: {correct_translation}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
