"""
Tests for trainer mode translation validation.
This test file validates the improved prompt logic without requiring external dependencies.
"""
import pytest
import sys
import os
from unittest.mock import AsyncMock, patch, MagicMock

# Add bot directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bot'))


def test_prompt_improvement():
    """Test that the improved prompt logic is in place."""
    # This is a simple validation test that checks the code changes exist
    with open('bot/services/translation_service.py', 'r') as f:
        content = f.read()
        
    # Check that the improved prompt includes key elements
    assert "First check if the user's answer is even attempting to translate" in content, \
        "Prompt should check for off-topic answers"
    assert "If off-topic" in content, \
        "Prompt should handle off-topic cases"
    assert "explanation in" in content.lower(), \
        "Prompt should specify language for explanations"
    assert "ORIGINAL sentence" in content, \
        "Prompt should reference the original sentence"
    
    print("✓ Prompt improvements are in place")


def test_generate_sentence_language_mapping():
    """Test that generate_sentence uses proper language names."""
    with open('bot/services/translation_service.py', 'r') as f:
        content = f.read()
    
    # Find the generate_sentence function
    assert 'async def generate_sentence' in content, \
        "generate_sentence function should exist"
    
    # Check that language mapping is present in generate_sentence
    assert content.count('lang_names = {') >= 2, \
        "Language name mapping should be in both check_translation and generate_sentence"
    
    # Verify Ukrainian is mapped
    assert content.count('"uk": "Ukrainian"') >= 2, \
        "Ukrainian language mapping should be present"
    
    # Verify Russian is mapped
    assert content.count('"ru": "Russian"') >= 2, \
        "Russian language mapping should be present"
    
    print("✓ Language mapping is present in generate_sentence")


@pytest.mark.asyncio
async def test_check_translation_off_topic_answer():
    """Test that completely off-topic answers are rejected with low quality."""
    # Mock all dependencies to avoid import errors
    sys.modules['redis'] = MagicMock()
    sys.modules['redis.asyncio'] = MagicMock()
    
    from bot.services.translation_service import TranslationService
    
    # Mock OpenAI response for off-topic answer
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = """STATUS: INCORRECT
TRANSLATION: Ich spiele gerne Fußball mit meinen Freunden.
QUALITY: 10
EXPLANATION: Ваша відповідь "Собака" зовсім не відноситься до завдання. Потрібно було перекласти речення "I like to play football with my friends" німецькою мовою."""
    
    with patch.object(TranslationService, '__init__', lambda self: None):
        service = TranslationService()
        service.client = MagicMock()
        service.client.chat = MagicMock()
        service.client.chat.completions = MagicMock()
        service.client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        # Test off-topic answer
        is_correct, correct_translation, explanation, quality = await service.check_translation(
            original="I like to play football with my friends",
            user_translation="Собака",
            expected_lang="de",
            interface_lang="uk"
        )
        
        assert is_correct == False, "Off-topic answer should be marked as incorrect"
        assert quality <= 20, f"Off-topic answer should have low quality (<= 20%), got {quality}%"
        assert "Ich spiele gerne" in correct_translation, "Should provide correct German translation"
        assert "Собака" in explanation or "завдання" in explanation, "Explanation should mention the issue"


@pytest.mark.asyncio
async def test_check_translation_correct_answer():
    """Test that correct answers are accepted with high quality."""
    sys.modules['redis'] = MagicMock()
    sys.modules['redis.asyncio'] = MagicMock()
    
    from bot.services.translation_service import TranslationService
    
    # Mock OpenAI response for correct answer
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = """STATUS: CORRECT
TRANSLATION: Ich kann nichts
QUALITY: 90
EXPLANATION: Ваш переклад правильний і природній. Речення "Ich kann nichts" точно передає значення "I can't do anything"."""
    
    with patch.object(TranslationService, '__init__', lambda self: None):
        service = TranslationService()
        service.client = MagicMock()
        service.client.chat = MagicMock()
        service.client.chat.completions = MagicMock()
        service.client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        is_correct, correct_translation, explanation, quality = await service.check_translation(
            original="I can't do anything",
            user_translation="Ich kann nichts",
            expected_lang="de",
            interface_lang="uk"
        )
        
        assert is_correct == True, "Correct answer should be marked as correct"
        assert quality >= 80, f"Correct answer should have high quality (>= 80%), got {quality}%"


@pytest.mark.asyncio
async def test_check_translation_interface_language():
    """Test that explanations are in the correct interface language."""
    sys.modules['redis'] = MagicMock()
    sys.modules['redis.asyncio'] = MagicMock()
    
    from bot.services.translation_service import TranslationService
    
    # Mock OpenAI response with Russian explanation
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = """STATUS: INCORRECT
TRANSLATION: Ich lese gerne Bücher am Abend.
QUALITY: 15
EXPLANATION: Ваш ответ "Ich kann nichts" не соответствует заданию. Нужно было перевести предложение "I like to read books in the evening" на немецкий язык."""
    
    with patch.object(TranslationService, '__init__', lambda self: None):
        service = TranslationService()
        service.client = MagicMock()
        service.client.chat = MagicMock()
        service.client.chat.completions = MagicMock()
        service.client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        # Test with Russian interface language
        is_correct, correct_translation, explanation, quality = await service.check_translation(
            original="I like to read books in the evening",
            user_translation="Ich kann nichts",
            expected_lang="de",
            interface_lang="ru"
        )
        
        assert is_correct == False
        # Check that explanation contains Russian text (Cyrillic characters)
        assert any(ord(c) >= 0x400 and ord(c) <= 0x4FF for c in explanation), \
            "Explanation should be in Russian (contain Cyrillic)"


@pytest.mark.asyncio
async def test_check_translation_partial_correct():
    """Test that partially correct answers get medium quality scores."""
    sys.modules['redis'] = MagicMock()
    sys.modules['redis.asyncio'] = MagicMock()
    
    from bot.services.translation_service import TranslationService
    
    # Mock OpenAI response for partial correct answer
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = """STATUS: INCORRECT
TRANSLATION: Ich spiele gerne Fußball mit meinen Freunden.
QUALITY: 60
EXPLANATION: Ваш переклад передає загальний зміст, але має граматичні помилки."""
    
    with patch.object(TranslationService, '__init__', lambda self: None):
        service = TranslationService()
        service.client = MagicMock()
        service.client.chat = MagicMock()
        service.client.chat.completions = MagicMock()
        service.client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        is_correct, correct_translation, explanation, quality = await service.check_translation(
            original="I like to play football with my friends",
            user_translation="Ich spiele Fußball mit Freunden",
            expected_lang="de",
            interface_lang="uk"
        )
        
        assert is_correct == False
        assert 40 <= quality <= 70, f"Partially correct answer should have medium quality, got {quality}%"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
