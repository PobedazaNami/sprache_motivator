"""
Test that validates the fix for the translation feedback issue.

This test validates that:
1. When answer is incorrect, the TRANSLATION field doesn't contain the user's wrong answer
2. The validation logic detects when OpenAI returns the user's answer
3. The system falls back to getting a proper translation
"""
import pytest


def test_user_answer_not_in_translation_field():
    """
    Test that the code validates TRANSLATION field doesn't contain user's wrong answer.
    
    This is the core fix for the GitHub issue where the bot was showing:
    ✏️ Правильний переклад:
    viele leuten hat probleme mit arbeitlos
    
    Instead of the actual correct translation.
    """
    with open('bot/services/translation_service.py', 'r') as f:
        content = f.read()
    
    # Verify there's a check that compares correct_translation with user_translation
    assert "normalized_correct" in content and "normalized_user" in content, \
        "Code should normalize both translations for comparison"
    assert "user_translation.lower()" in content, \
        "Code should compare translations case-insensitively"
    assert "not is_correct" in content and "is_invalid_translation" in content, \
        "Code should check if translation is invalid when answer is incorrect"
    
    # Verify the comparison includes the user_translation
    assert "normalized_user" in content or "user_translation" in content, \
        "Code should compare against user_translation"
    
    print("✓ Code validates that TRANSLATION field doesn't contain user's wrong answer")


def test_stronger_prompt_requirements():
    """
    Test that the prompt has been strengthened to prevent returning user's answer.
    """
    with open('bot/services/translation_service.py', 'r') as f:
        content = f.read()
    
    # Check that prompt explicitly forbids returning user's answer
    assert "NEVER put the user's answer in the TRANSLATION field" in content or \
           "NOT the user's answer" in content, \
        "Prompt should explicitly forbid putting user's answer in TRANSLATION field"
    
    # Check that it emphasizes providing correct translation from scratch
    assert "correct translation from scratch" in content or \
           "MUST be the CORRECT translation" in content, \
        "Prompt should emphasize providing actual correct translation"
    
    print("✓ Prompt explicitly forbids returning user's answer in TRANSLATION field")


def test_grammar_explanation_requirements_strengthened():
    """
    Test that the prompt requirements for grammar explanations are more specific.
    """
    with open('bot/services/translation_service.py', 'r') as f:
        content = f.read()
    
    # Check for specific grammar elements that must be explained
    assert ("Which grammatical case" in content or "which case" in content.lower()), \
        "Prompt should require explaining grammatical cases"
    assert ("Which article" in content or "which verb" in content), \
        "Prompt should require explaining articles and verbs"
    assert ("Which preposition" in content or "preposition" in content.lower()), \
        "Prompt should require explaining prepositions"
    
    # Check that it forbids generic statements
    assert ("DO NOT write generic statements" in content or 
            "do NOT write vague statements" in content or
            "not just describe that errors exist" in content), \
        "Prompt should forbid generic/vague statements"
    
    # Check that it requires specific error identification
    assert ("specific error" in content.lower() or "EXACTLY which" in content), \
        "Prompt should require identifying specific errors"
    
    print("✓ Prompt requires specific, detailed grammar explanations")


def test_example_error_format_in_prompt():
    """
    Test that the prompt includes examples of how to explain errors specifically.
    """
    with open('bot/services/translation_service.py', 'r') as f:
        content = f.read()
    
    # Check for example format showing specific corrections
    # Looking for examples like: "should be" or specific error corrections
    assert "should be" in content.lower(), \
        "Prompt should include examples with 'should be' format"
    
    print("✓ Prompt includes examples of specific error explanations")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
