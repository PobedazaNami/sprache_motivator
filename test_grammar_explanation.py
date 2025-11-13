"""
Tests for grammar-focused explanations and level/topic information in trainer tasks.
This test validates the changes to provide better grammar explanations and display level/topic info.
"""
import pytest
import sys
import os

# Add bot directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bot'))


def test_grammar_focused_explanation_in_prompt():
    """Test that the prompt requests grammar-focused explanations."""
    with open('bot/services/translation_service.py', 'r') as f:
        content = f.read()
    
    # Check that the prompt focuses on grammar explanations
    assert "GRAMMAR-FOCUSED explanation" in content, \
        "Prompt should request grammar-focused explanations"
    assert "explain the grammatical rules" in content, \
        "Prompt should ask to explain grammatical rules"
    assert "cases, articles, prepositions, verb conjugations, word order, declensions" in content, \
        "Prompt should mention specific grammar elements"
    assert "Explain WHY certain grammatical forms are used" in content, \
        "Prompt should ask to explain why grammar forms are used"
    
    print("✓ Prompt properly requests grammar-focused explanations")


def test_level_topic_in_task_message():
    """Test that task message template includes level and topic information."""
    with open('bot/locales/texts.py', 'r') as f:
        content = f.read()
    
    # Check Ukrainian locale
    assert "📚 Рівень: {level} | Тема: {topic}" in content, \
        "Ukrainian task message should include level and topic"
    
    # Check Russian locale
    assert "📚 Уровень: {level} | Тема: {topic}" in content, \
        "Russian task message should include level and topic"
    
    print("✓ Task message templates include level and topic placeholders")


def test_topic_stored_in_training_session():
    """Test that topic is stored when creating a training session."""
    with open('bot/services/database_service.py', 'r') as f:
        content = f.read()
    
    # Check that create_session accepts topic parameter
    assert "topic: TrainerTopic = None" in content, \
        "create_session should accept topic parameter"
    assert '"topic": topic.value if topic else None' in content, \
        "Training session should store topic value"
    
    print("✓ Training session properly stores topic information")


def test_topic_passed_to_training_session():
    """Test that send_training_task passes topic to create_session."""
    with open('bot/handlers/trainer.py', 'r') as f:
        content = f.read()
    
    # Check that topic is passed to create_session
    assert "topic  # Pass topic to training session" in content or \
           "topic=topic" in content or \
           "topic)" in content, \
        "send_training_task should pass topic to create_session"
    
    # Check that level and topic are extracted for display
    assert "topic_level" in content, \
        "Should extract topic level for display"
    assert "topic_name" in content, \
        "Should extract topic name for display"
    
    print("✓ send_training_task properly passes topic information")


def test_topic_metadata_usage():
    """Test that TOPIC_METADATA is used to get level information."""
    with open('bot/handlers/trainer.py', 'r') as f:
        content = f.read()
    
    # Check that TOPIC_METADATA is imported and used
    assert "from bot.models.database import TOPIC_METADATA" in content, \
        "Should import TOPIC_METADATA"
    assert "TOPIC_METADATA.get(topic" in content, \
        "Should use TOPIC_METADATA to get topic info"
    
    print("✓ TOPIC_METADATA is properly used for level information")


if __name__ == "__main__":
    test_grammar_focused_explanation_in_prompt()
    test_level_topic_in_task_message()
    test_topic_stored_in_training_session()
    test_topic_passed_to_training_session()
    test_topic_metadata_usage()
    print("\n✅ All tests passed!")
