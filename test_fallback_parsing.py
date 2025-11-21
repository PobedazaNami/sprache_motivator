"""
Test the improved fallback parsing for non-JSON responses.

This test validates that when OpenAI returns a response that isn't valid JSON,
the system can still extract meaningful explanations instead of just showing
a generic parser error.
"""
import asyncio
import types
import pytest
from bot.services.translation_service import TranslationService
from bot.config import settings

pytestmark = pytest.mark.asyncio


class FakeChoice:
    def __init__(self, content: str):
        self.message = types.SimpleNamespace(content=content)


class FakeResponse:
    def __init__(self, content: str):
        self.choices = [FakeChoice(content)]
        self.usage = types.SimpleNamespace(total_tokens=42)


class FakeChat:
    def __init__(self, content: str):
        self._content = content

    async def create(self, **kwargs):
        return FakeResponse(self._content)


class FakeOpenAIClient:
    def __init__(self, content: str):
        self.chat = types.SimpleNamespace(completions=types.SimpleNamespace(create=FakeChat(content).create))


async def make_service(llm_response: str, lt_matches=None) -> TranslationService:
    """Create a translation service with mocked OpenAI response."""
    svc = TranslationService()
    svc.client = FakeOpenAIClient(llm_response)
    
    async def fake_lt(text: str, language: str):
        return lt_matches or []
    
    svc._languagetool_check = fake_lt
    settings.LANGUAGETOOL_ENABLED = lt_matches is not None
    return svc


async def test_valid_json_parsing():
    """Test that valid JSON is parsed correctly."""
    llm_json = '{"status":"INCORRECT","correct":"Ich möchte in der Zukunft Arzt werden.","quality":75,"errors":["Отсутствует предлог в начале","Порядок слов не идеален"]}'
    svc = await make_service(llm_json, lt_matches=[])
    
    is_correct, correct, explanation, quality = await svc.check_translation(
        original="Я хочу стати лікарем у майбутньому.",
        user_translation="Ich möchte Arzt in der Zukunft werden.",
        expected_lang="de",
        interface_lang="uk",
    )
    
    assert is_correct is False
    assert quality > 0
    assert "Отсутствует предлог" in explanation or "Порядок слов" in explanation
    assert "Arzt" in correct


async def test_json_embedded_in_text():
    """Test extraction of JSON from text with surrounding content."""
    llm_response = '''Here's my evaluation:
{"status":"INCORRECT","correct":"Ich möchte in der Zukunft Arzt werden.","quality":70,"errors":["Неправильный порядок слов: 'in der Zukunft' должно быть в начале или в конце","Отсутствует артикль перед профессией при использовании 'werden'"]}
Hope this helps!'''
    
    svc = await make_service(llm_response, lt_matches=[])
    
    is_correct, correct, explanation, quality = await svc.check_translation(
        original="Я хочу стати лікарем у майбутньому.",
        user_translation="Ich möchte Arzt in der Zukunft werden.",
        expected_lang="de",
        interface_lang="ru",
    )
    
    assert is_correct is False
    assert quality >= 70
    # Should extract the actual errors from the JSON, not show generic message
    assert "Неправильный порядок слов" in explanation or "артикль" in explanation
    assert "Автоматический парсер" not in explanation
    assert "Arzt" in correct


async def test_structured_text_fallback():
    """Test parsing of structured text when JSON is completely invalid."""
    llm_response = '''Status: INCORRECT
    
Errors found:
- Неправильный порядок слов: 'in der Zukunft' должно стоять в другом месте
- Отсутствует артикль перед 'Arzt' при использовании глагола 'werden'
- Предлог 'in' используется неверно в данном контексте

Correct translation: Ich möchte in der Zukunft Arzt werden.
Quality: 65%'''
    
    svc = await make_service(llm_response, lt_matches=[])
    
    is_correct, correct, explanation, quality = await svc.check_translation(
        original="Я хочу стати лікарем у майбутньому.",
        user_translation="Ich möchte Arzt in der Zukunft werden.",
        expected_lang="de",
        interface_lang="ru",
    )
    
    assert is_correct is False
    # Should extract actual error descriptions from the text
    assert "порядок слов" in explanation.lower() or "артикль" in explanation.lower()
    # Should not show the generic parser error
    assert "Автоматический парсер" not in explanation


async def test_no_useful_info_fallback_ukrainian():
    """Test that we provide helpful Ukrainian message when no info can be extracted."""
    llm_response = "Internal error processing your request"
    
    svc = await make_service(llm_response, lt_matches=[])
    
    is_correct, correct, explanation, quality = await svc.check_translation(
        original="Я хочу стати лікарем у майбутньому.",
        user_translation="Ich möchte Arzt in der Zukunft werden.",
        expected_lang="de",
        interface_lang="uk",
    )
    
    assert is_correct is False
    # Should show helpful Ukrainian message
    assert "граматиці" in explanation or "помилки" in explanation
    # Should not show the old generic Russian message
    assert "Автоматический парсер" not in explanation


async def test_no_useful_info_fallback_russian():
    """Test that we provide helpful Russian message when no info can be extracted."""
    llm_response = "Error: Unable to process"
    
    svc = await make_service(llm_response, lt_matches=[])
    
    is_correct, correct, explanation, quality = await svc.check_translation(
        original="Я хочу стать врачом в будущем.",
        user_translation="Ich möchte Arzt in der Zukunft werden.",
        expected_lang="de",
        interface_lang="ru",
    )
    
    assert is_correct is False
    # Should show helpful Russian message
    assert "грамматике" in explanation or "ошибки" in explanation
    # Should not show the old generic parser message
    assert "Автоматический парсер" not in explanation


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
