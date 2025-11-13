import asyncio
import types
import pytest

# Use pytest-asyncio
pytestmark = pytest.mark.asyncio

from bot.services.translation_service import TranslationService
from bot.config import settings


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


class FakeCompletions:
    def __init__(self, content: str):
        self.chat = types.SimpleNamespace(completions=types.SimpleNamespace(create=FakeChat(content).create))


class FakeOpenAIClient:
    def __init__(self, content: str):
        # Provide attribute access like client.chat.completions.create
        self.chat = types.SimpleNamespace(completions=types.SimpleNamespace(create=FakeChat(content).create))


async def make_service(overridden_llm_json: str, lt_matches=None) -> TranslationService:
    svc = TranslationService()
    # Patch OpenAI client to return our JSON
    svc.client = FakeOpenAIClient(overridden_llm_json)

    # Patch LT checker
    async def fake_lt(text: str, language: str):
        return lt_matches or []

    svc._languagetool_check = fake_lt  # type: ignore
    # Ensure LT integration doesn't affect tests unless explicitly provided
    settings.LANGUAGETOOL_ENABLED = lt_matches is not None
    return svc


async def test_perfect_answer_remains_correct():
    # LLM says CORRECT, LT finds nothing, DE heuristics none
    llm_json = '{"status":"CORRECT","correct":"Ich gehe jeden Tag zur Arbeit.","quality":100,"errors":[]}'
    svc = await make_service(llm_json, lt_matches=[])
    is_correct, correct, explanation, quality = await svc.check_translation(
        original="I go to work every day.",
        user_translation="Ich gehe jeden Tag zur Arbeit.",
        expected_lang="de",
        interface_lang="ru",
    )
    print("DEBUG:", is_correct, quality, explanation)
    assert is_correct is True
    assert quality >= 90
    assert "без грамматических ошибок" in explanation.lower()
    assert correct.startswith("Ich gehe")


async def test_heuristics_overrule_llm_when_typo_jeden_tag():
    # LLM incorrectly says CORRECT, but user has 'eden Tag' typo
    llm_json = '{"status":"CORRECT","correct":"Ich gehe jeden Tag zur Arbeit.","quality":95,"errors":[]}'
    svc = await make_service(llm_json, lt_matches=[])  # LT empty to validate heuristic
    is_correct, correct, explanation, quality = await svc.check_translation(
        original="I go to work every day.",
        user_translation="Ich gehe eden Tag zur Arbeit.",
        expected_lang="de",
        interface_lang="ru",
    )
    assert is_correct is False
    assert quality < 95
    assert "jeden Tag" in explanation or "jeden" in explanation


async def test_languagetool_forces_incorrect():
    # LLM says CORRECT, but LT finds an issue (e.g., wrong article or case)
    llm_json = '{"status":"CORRECT","correct":"Ich besuche die Schule.","quality":96,"errors":[]}'
    lt_matches = [
        {
            "message": "Falscher Kasus nach Präposition.",
            "shortMessage": "Kasus",
            "offset": 12,
            "length": 6,
            "rule": {"id": "DE_CASE_RULE"},
        }
    ]
    svc = await make_service(llm_json, lt_matches=lt_matches)
    is_correct, correct, explanation, quality = await svc.check_translation(
        original="I go to school.",
        user_translation="Ich gehe in die Schule.",
        expected_lang="de",
        interface_lang="ru",
    )
    assert is_correct is False
    assert any(part.startswith("[LT]") for part in explanation.splitlines())
    assert quality < 96
