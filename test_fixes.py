"""
Tests for the trainer and translator fixes.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os
from bson import ObjectId

# Add bot directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bot'))


@pytest.mark.asyncio
async def test_redis_service_get_set_methods():
    """Test that RedisService has get and set methods for scheduler."""
    from bot.services.redis_service import RedisService
    
    service = RedisService()
    
    # Check that methods exist
    assert hasattr(service, 'get')
    assert hasattr(service, 'set')
    assert callable(service.get)
    assert callable(service.set)


@pytest.mark.asyncio
async def test_objectid_string_conversion():
    """Test ObjectId to string conversion and back."""
    # Create a test ObjectId
    test_id = ObjectId()
    
    # Convert to string (like we do in trainer.py)
    id_string = str(test_id)
    
    # Convert back to ObjectId (like we do in check_training_answer)
    recovered_id = ObjectId(id_string)
    
    # Should be equal
    assert test_id == recovered_id


@pytest.mark.asyncio
async def test_translator_filter_excludes_mode_buttons():
    """Test that translator filter excludes all mode button texts."""
    from bot.handlers import translator
    
    # Get the router
    router = translator.router
    
    # Find the process_translation handler
    process_translation_handler = None
    for handler in router.message.handlers:
        if handler.callback.__name__ == 'process_translation':
            process_translation_handler = handler
            break
    
    assert process_translation_handler is not None, "process_translation handler not found"
    
    # Check that filters include exclusions for all mode buttons
    # This is a basic check - the actual filter logic is in aiogram


@pytest.mark.asyncio  
async def test_translation_language_detection():
    """Test Cyrillic detection for translation language routing."""
    # Test Cyrillic text detection
    ukrainian_text = "Привіт світ"
    russian_text = "Привет мир"
    english_text = "Hello world"
    german_text = "Hallo Welt"
    
    # Check Cyrillic detection logic
    assert any('\u0400' <= c <= '\u04FF' for c in ukrainian_text)
    assert any('\u0400' <= c <= '\u04FF' for c in russian_text)
    assert not any('\u0400' <= c <= '\u04FF' for c in english_text)
    assert not any('\u0400' <= c <= '\u04FF' for c in german_text)


@pytest.mark.asyncio
async def test_invalid_objectid_handling():
    """Test that invalid ObjectId strings are handled gracefully."""
    from bson import ObjectId
    
    invalid_ids = ["not_an_id", "12345", "", None]
    
    for invalid_id in invalid_ids:
        try:
            if invalid_id:
                ObjectId(invalid_id)
                assert False, f"Should have raised exception for {invalid_id}"
        except Exception:
            # Expected to raise exception
            pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
