"""
Test for mode switching fix - ensuring trainer mode button works even when in translator state.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Add bot directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bot'))


@pytest.mark.asyncio
async def test_trainer_handler_in_start_router():
    """Test that trainer mode handler exists in start.router."""
    from bot.handlers import start
    
    # Check that start router has the trainer mode handler
    router = start.router
    
    # Find handler for trainer mode button
    trainer_handler_found = False
    for handler in router.message.handlers:
        if handler.callback.__name__ == 'switch_to_trainer':
            trainer_handler_found = True
            break
    
    assert trainer_handler_found, "switch_to_trainer handler not found in start.router"
    print("✓ Trainer mode handler found in start.router")


@pytest.mark.asyncio
async def test_trainer_button_text_consistency():
    """Test that trainer button texts are consistent across files."""
    from bot.locales.texts import get_text
    
    # Get button texts from locales
    uk_text = get_text("uk", "btn_daily_trainer")
    ru_text = get_text("ru", "btn_daily_trainer")
    
    # Texts that should be handled by start router
    start_texts = ["🎯 Ежедневный тренажёр", "🎯 Щоденний тренажер"]
    
    # Texts that should be excluded in translator
    from bot.handlers.translator import router as translator_router
    
    # Get the process_translation handler
    process_translation_handler = None
    for handler in translator_router.message.handlers:
        if handler.callback.__name__ == 'process_translation':
            process_translation_handler = handler
            break
    
    assert process_translation_handler is not None
    
    # Verify consistency
    assert uk_text in start_texts, f"Ukrainian trainer button '{uk_text}' should be in start handler list"
    assert ru_text in start_texts, f"Russian trainer button '{ru_text}' should be in start handler list"
    
    print(f"✓ Ukrainian trainer button: '{uk_text}'")
    print(f"✓ Russian trainer button: '{ru_text}'")
    print("✓ Button texts are consistent")


@pytest.mark.asyncio
async def test_start_router_registered_first():
    """Test that start router is registered before translator router."""
    from bot.main import main
    import inspect
    
    # Get source code of main function
    source = inspect.getsource(main)
    
    # Check that start.router appears before translator.router
    start_pos = source.find('start.router')
    translator_pos = source.find('translator.router')
    
    assert start_pos > 0, "start.router not found in main()"
    assert translator_pos > 0, "translator.router not found in main()"
    assert start_pos < translator_pos, "start.router should be registered before translator.router"
    
    print("✓ Router registration order is correct")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
