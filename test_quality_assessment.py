"""
Tests for enhanced translation quality assessment.
This test validates that the quality evaluation considers punctuation, word endings, and semantic meaning.
"""
import pytest
import sys
import os
from unittest.mock import AsyncMock, patch, MagicMock

# Add bot directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bot'))


def test_quality_criteria_in_prompt():
    """Test that the prompt includes specific quality criteria."""
    with open('bot/services/translation_service.py', 'r') as f:
        content = f.read()
    
    # Check that the prompt includes specific quality criteria
    assert "Punctuation correctness" in content, \
        "Prompt should mention punctuation correctness"
    assert "Word endings and grammar" in content, \
        "Prompt should mention word endings and grammar"
    assert "Semantic accuracy" in content, \
        "Prompt should mention semantic accuracy"
    assert "weight" in content.lower(), \
        "Prompt should specify weights for quality criteria"
    assert "declensions, conjugations" in content, \
        "Prompt should mention declensions and conjugations"
    assert "specifically mention if there are errors in: punctuation, word endings, or semantic meaning" in content, \
        "Prompt should require mentioning specific error types in explanation"
    
    print("✓ Quality criteria are properly specified in the prompt")


def test_localization_mentions_quality_factors():
    """Test that user-facing messages mention quality evaluation factors."""
    with open('bot/locales/texts.py', 'r') as f:
        content = f.read()
    
    # Check Ukrainian locale
    assert "Оцінка враховує: пунктуацію, закінчення слів та точність значення" in content, \
        "Ukrainian locale should mention quality factors"
    
    # Check Russian locale
    assert "Оценка учитывает: пунктуацию, окончания слов и точность значения" in content, \
        "Russian locale should mention quality factors"
    
    print("✓ Localization texts properly explain quality factors")


@pytest.mark.asyncio
async def test_punctuation_error_quality():
    """Test that punctuation errors are reflected in quality score."""
    sys.modules['redis'] = MagicMock()
    sys.modules['redis.asyncio'] = MagicMock()
    
    from bot.services.translation_service import TranslationService
    
    # Mock OpenAI response for translation with punctuation error
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = """STATUS: INCORRECT
TRANSLATION: Ich gehe gerne spazieren, wenn das Wetter schön ist.
QUALITY: 75
EXPLANATION: Ваш переклад майже правильний, але є помилка з пунктуацією: після "spazieren" повинна бути кома, оскільки це підрядне речення. Загальний зміст передано правильно, але пунктуація впливає на якість перекладу."""
    
    with patch.object(TranslationService, '__init__', lambda self: None):
        service = TranslationService()
        service.client = MagicMock()
        service.client.chat = MagicMock()
        service.client.chat.completions = MagicMock()
        service.client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        is_correct, correct_translation, explanation, quality = await service.check_translation(
            original="I like to go for walks when the weather is nice",
            user_translation="Ich gehe gerne spazieren wenn das Wetter schön ist",
            expected_lang="de",
            interface_lang="uk"
        )
        
        assert is_correct == False, "Translation with punctuation error should be marked incorrect"
        assert 65 <= quality <= 85, f"Punctuation error should result in medium-high quality (65-85%), got {quality}%"
        assert "пунктуац" in explanation.lower() or "кома" in explanation.lower(), \
            "Explanation should mention punctuation error"


@pytest.mark.asyncio
async def test_word_ending_error_quality():
    """Test that word ending errors are reflected in quality score."""
    sys.modules['redis'] = MagicMock()
    sys.modules['redis.asyncio'] = MagicMock()
    
    from bot.services.translation_service import TranslationService
    
    # Mock OpenAI response for translation with word ending error
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = """STATUS: INCORRECT
TRANSLATION: Ich habe gestern mit meinem Freund gesprochen.
QUALITY: 70
EXPLANATION: Ваш переклад має помилку в закінченні слова: замість "Freunden" повинно бути "Freund" (однина, оскільки мова йде про одного друга). Закінчення слів в німецькій мові дуже важливі для правильного відмінювання."""
    
    with patch.object(TranslationService, '__init__', lambda self: None):
        service = TranslationService()
        service.client = MagicMock()
        service.client.chat = MagicMock()
        service.client.chat.completions = MagicMock()
        service.client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        is_correct, correct_translation, explanation, quality = await service.check_translation(
            original="I spoke with my friend yesterday",
            user_translation="Ich habe gestern mit meinem Freunden gesprochen",
            expected_lang="de",
            interface_lang="uk"
        )
        
        assert is_correct == False, "Translation with word ending error should be marked incorrect"
        assert 60 <= quality <= 80, f"Word ending error should result in medium quality (60-80%), got {quality}%"
        assert "закінчен" in explanation.lower() or "відмін" in explanation.lower(), \
            "Explanation should mention word ending error"


@pytest.mark.asyncio
async def test_semantic_error_quality():
    """Test that semantic errors result in lower quality scores."""
    sys.modules['redis'] = MagicMock()
    sys.modules['redis.asyncio'] = MagicMock()
    
    from bot.services.translation_service import TranslationService
    
    # Mock OpenAI response for translation with semantic error
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = """STATUS: INCORRECT
TRANSLATION: Ich liebe es, abends Bücher zu lesen.
QUALITY: 30
EXPLANATION: Ваш переклад має семантичну помилку: ви переклали "ненавиджу" (hate) як "liebe" (love), що є протилежним значенням. Це повністю змінює зміст речення. Правильний переклад повинен використовувати "hasse" або "mag nicht"."""
    
    with patch.object(TranslationService, '__init__', lambda self: None):
        service = TranslationService()
        service.client = MagicMock()
        service.client.chat = MagicMock()
        service.client.chat.completions = MagicMock()
        service.client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        is_correct, correct_translation, explanation, quality = await service.check_translation(
            original="I hate reading books in the evening",
            user_translation="Ich liebe es, abends Bücher zu lesen",
            expected_lang="de",
            interface_lang="uk"
        )
        
        assert is_correct == False, "Translation with semantic error should be marked incorrect"
        assert quality <= 40, f"Semantic error should result in low quality (<= 40%), got {quality}%"
        assert "семантич" in explanation.lower() or "зміст" in explanation.lower() or "значенн" in explanation.lower(), \
            "Explanation should mention semantic error"


@pytest.mark.asyncio
async def test_perfect_translation_high_quality():
    """Test that perfect translations get very high quality scores."""
    sys.modules['redis'] = MagicMock()
    sys.modules['redis.asyncio'] = MagicMock()
    
    from bot.services.translation_service import TranslationService
    
    # Mock OpenAI response for perfect translation
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = """STATUS: CORRECT
TRANSLATION: Ich gehe jeden Morgen joggen, wenn das Wetter gut ist.
QUALITY: 98
EXPLANATION: Ваш переклад ідеальний! Пунктуація правильна, закінчення слів точні, і семантичне значення повністю відповідає оригіналу. Речення звучить природньо німецькою мовою."""
    
    with patch.object(TranslationService, '__init__', lambda self: None):
        service = TranslationService()
        service.client = MagicMock()
        service.client.chat = MagicMock()
        service.client.chat.completions = MagicMock()
        service.client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        is_correct, correct_translation, explanation, quality = await service.check_translation(
            original="I go jogging every morning when the weather is good",
            user_translation="Ich gehe jeden Morgen joggen, wenn das Wetter gut ist",
            expected_lang="de",
            interface_lang="uk"
        )
        
        assert is_correct == True, "Perfect translation should be marked correct"
        assert quality >= 95, f"Perfect translation should have very high quality (>= 95%), got {quality}%"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
