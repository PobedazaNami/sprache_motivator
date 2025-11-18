"""
Test support messaging feature where users can send messages to admins
and admins can reply back to users.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.types import Message, User, Chat
from aiogram.fsm.context import FSMContext

from bot.handlers.settings import support_message, receive_support_message, handle_admin_reply, SupportStates
from bot.models.database import UserStatus, InterfaceLanguage
from bot.locales.texts import get_text


@pytest.fixture
def mock_user():
    """Create a mock user"""
    user = MagicMock()
    user.telegram_id = 12345
    user.first_name = "Test"
    user.last_name = "User"
    user.username = "testuser"
    user.status = UserStatus.APPROVED
    user.interface_language = InterfaceLanguage.RUSSIAN
    return user


@pytest.fixture
def mock_message():
    """Create a mock message"""
    message = AsyncMock(spec=Message)
    message.from_user = MagicMock(spec=User)
    message.from_user.id = 12345
    message.from_user.username = "testuser"
    message.from_user.first_name = "Test"
    message.text = "💬 Техподдержка"
    message.chat = MagicMock(spec=Chat)
    message.answer = AsyncMock()
    message.reply = AsyncMock()
    message.copy_to = AsyncMock()
    message.bot = AsyncMock()
    message.bot.send_message = AsyncMock()
    return message


@pytest.fixture
def mock_state():
    """Create a mock FSM state"""
    state = AsyncMock(spec=FSMContext)
    state.set_state = AsyncMock()
    state.clear = AsyncMock()
    state.get_data = AsyncMock(return_value={})
    return state


@pytest.mark.asyncio
async def test_support_message_initiates_conversation(mock_message, mock_state, mock_user):
    """Test that clicking support button initiates conversation"""
    with patch('bot.handlers.settings.async_session_maker') as mock_session:
        # Setup mock session
        mock_session_instance = AsyncMock()
        mock_session.return_value.__aenter__.return_value = mock_session_instance
        mock_session.return_value.__aexit__ = AsyncMock()
        
        with patch('bot.handlers.settings.UserService.get_or_create_user', return_value=mock_user):
            # Call the handler
            await support_message(mock_message, mock_state)
            
            # Check that prompt message was sent
            mock_message.answer.assert_called_once()
            call_args = mock_message.answer.call_args
            assert "Напишите свое сообщение" in call_args[0][0]
            
            # Check that state was set
            mock_state.set_state.assert_called_once_with(SupportStates.waiting_for_message)


@pytest.mark.asyncio
async def test_receive_support_message_sends_to_admins(mock_message, mock_state, mock_user):
    """Test that user message is forwarded to admins"""
    mock_message.text = "У меня проблема с ботом"
    
    with patch('bot.handlers.settings.async_session_maker') as mock_session:
        # Setup mock session
        mock_session_instance = AsyncMock()
        mock_session.return_value.__aenter__.return_value = mock_session_instance
        mock_session.return_value.__aexit__ = AsyncMock()
        
        with patch('bot.handlers.settings.UserService.get_or_create_user', return_value=mock_user):
            with patch('bot.handlers.settings.settings') as mock_settings:
                mock_settings.admin_id_list = [99999]
                
                # Call the handler
                await receive_support_message(mock_message, mock_state)
                
                # Check that confirmation was sent to user
                assert mock_message.answer.call_count >= 1
                
                # Check that message was sent to admin
                assert mock_message.bot.send_message.called
                admin_call = None
                for call in mock_message.bot.send_message.call_args_list:
                    if call[0][0] == 99999:  # admin_id
                        admin_call = call
                        break
                
                assert admin_call is not None, "Message should be sent to admin"
                assert "ID: 12345" in admin_call[0][1]  # User ID should be in message
                
                # Check that state was cleared
                mock_state.clear.assert_called_once()


@pytest.mark.asyncio
async def test_admin_reply_forwarded_to_user(mock_message, mock_user):
    """Test that admin reply is forwarded back to user"""
    # Setup admin reply message
    mock_message.from_user.id = 99999  # Admin ID
    mock_message.text = "Мы разберемся с проблемой"
    
    # Setup replied-to message with user info
    mock_message.reply_to_message = MagicMock()
    mock_message.reply_to_message.text = "📩 Сообщение от пользователя:\n\n👤 Test User\n@testuser\nID: 12345\n\n💬 Сообщение:\nУ меня проблема"
    
    with patch('bot.handlers.settings.async_session_maker') as mock_session:
        # Setup mock session
        mock_session_instance = AsyncMock()
        mock_session.return_value.__aenter__.return_value = mock_session_instance
        mock_session.return_value.__aexit__ = AsyncMock()
        
        with patch('bot.handlers.settings.UserService.get_or_create_user', return_value=mock_user):
            with patch('bot.handlers.settings.settings') as mock_settings:
                mock_settings.admin_id_list = [99999]
                
                # Call the handler
                await handle_admin_reply(mock_message)
                
                # Check that reply was sent to user
                mock_message.bot.send_message.assert_called()
                user_call = None
                for call in mock_message.bot.send_message.call_args_list:
                    if call[0][0] == 12345:  # user_id
                        user_call = call
                        break
                
                assert user_call is not None, "Reply should be sent to user"
                assert "Ответ от администратора" in user_call[0][1]
                assert "Мы разберемся с проблемой" in user_call[0][1]


@pytest.mark.asyncio
async def test_cancel_support_returns_to_menu(mock_message, mock_state, mock_user):
    """Test that cancel button returns user to main menu"""
    mock_message.text = "🔙 Главное меню"
    
    with patch('bot.handlers.settings.async_session_maker') as mock_session:
        # Setup mock session
        mock_session_instance = AsyncMock()
        mock_session.return_value.__aenter__.return_value = mock_session_instance
        mock_session.return_value.__aexit__ = AsyncMock()
        
        with patch('bot.handlers.settings.UserService.get_or_create_user', return_value=mock_user):
            # Call the handler
            await receive_support_message(mock_message, mock_state)
            
            # Check that state was cleared
            mock_state.clear.assert_called_once()
            
            # Check that main menu was shown
            assert mock_message.answer.call_count >= 1


def test_localization_strings_exist():
    """Test that all required localization strings exist"""
    for lang in ["uk", "ru"]:
        assert get_text(lang, "support_prompt") is not None
        assert get_text(lang, "support_message_sent") is not None
        assert get_text(lang, "support_admin_reply") is not None
        assert get_text(lang, "btn_cancel") is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
