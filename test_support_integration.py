"""
Integration test demonstrating the complete support messaging flow.
This shows how the issue is resolved - users can now send messages to admins
and receive replies through the bot.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.types import Message, User
from aiogram.fsm.context import FSMContext

from bot.handlers.settings import support_message, receive_support_message, handle_admin_reply, SupportStates
from bot.models.database import UserStatus, InterfaceLanguage


class TestSupportMessagingIntegration:
    """Integration tests for the complete support messaging flow"""
    
    @pytest.mark.asyncio
    async def test_complete_support_conversation_flow(self):
        """
        Test the complete flow:
        1. User clicks support button
        2. User sends a message
        3. Admin receives the message
        4. Admin replies
        5. User receives the reply
        """
        # Setup
        user_id = 12345
        admin_id = 99999
        user_message_text = "У меня проблема с тренажером"
        admin_reply_text = "Мы разберемся с этой проблемой в ближайшее время"
        
        # Mock user
        mock_user = MagicMock()
        mock_user.telegram_id = user_id
        mock_user.first_name = "Ivan"
        mock_user.last_name = "Petrov"
        mock_user.username = "ivanpetrov"
        mock_user.status = UserStatus.APPROVED
        mock_user.interface_language = InterfaceLanguage.RUSSIAN
        
        # Mock state
        mock_state = AsyncMock(spec=FSMContext)
        mock_state.set_state = AsyncMock()
        mock_state.clear = AsyncMock()
        mock_state.get_data = AsyncMock(return_value={})
        
        # Mock bot
        mock_bot = AsyncMock()
        mock_bot.send_message = AsyncMock(return_value=MagicMock(message_id=1001))
        
        # STEP 1: User clicks support button
        user_click_message = AsyncMock(spec=Message)
        user_click_message.from_user = MagicMock(spec=User)
        user_click_message.from_user.id = user_id
        user_click_message.text = "💬 Техподдержка"
        user_click_message.answer = AsyncMock()
        user_click_message.bot = mock_bot
        
        with patch('bot.handlers.settings.async_session_maker') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_session_instance
            mock_session.return_value.__aexit__ = AsyncMock()
            
            with patch('bot.handlers.settings.UserService.get_or_create_user', return_value=mock_user):
                await support_message(user_click_message, mock_state)
                
                # Verify: User receives prompt to send message
                assert user_click_message.answer.called
                call_text = user_click_message.answer.call_args[0][0]
                assert "Напишите свое сообщение" in call_text
                
                # Verify: State is set to waiting for message
                mock_state.set_state.assert_called_once_with(SupportStates.waiting_for_message)
        
        # STEP 2: User sends their support message
        user_support_message = AsyncMock(spec=Message)
        user_support_message.from_user = MagicMock(spec=User)
        user_support_message.from_user.id = user_id
        user_support_message.text = user_message_text
        user_support_message.answer = AsyncMock()
        user_support_message.copy_to = AsyncMock()
        user_support_message.bot = mock_bot
        
        with patch('bot.handlers.settings.async_session_maker') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_session_instance
            mock_session.return_value.__aexit__ = AsyncMock()
            
            with patch('bot.handlers.settings.UserService.get_or_create_user', return_value=mock_user):
                with patch('bot.handlers.settings.settings') as mock_settings:
                    mock_settings.admin_id_list = [admin_id]
                    
                    await receive_support_message(user_support_message, mock_state)
                    
                    # Verify: User receives confirmation
                    assert user_support_message.answer.call_count >= 1
                    confirmation_call = user_support_message.answer.call_args_list[0]
                    assert "Ваше сообщение отправлено" in confirmation_call[0][0]
                    
                    # Verify: Admin receives the message with context
                    mock_bot.send_message.assert_called()
                    admin_message_call = None
                    for call in mock_bot.send_message.call_args_list:
                        if call[0][0] == admin_id:
                            admin_message_call = call
                            break
                    
                    assert admin_message_call is not None
                    admin_message_text = admin_message_call[0][1]
                    assert "ID: 12345" in admin_message_text
                    assert "@ivanpetrov" in admin_message_text
                    assert user_message_text in admin_message_text or "💬 Сообщение:" in admin_message_text
        
        # STEP 3 & 4: Admin replies to the message
        admin_reply_message = AsyncMock(spec=Message)
        admin_reply_message.from_user = MagicMock(spec=User)
        admin_reply_message.from_user.id = admin_id
        admin_reply_message.text = admin_reply_text
        admin_reply_message.reply = AsyncMock()
        admin_reply_message.bot = mock_bot
        
        # Admin is replying to a message that contains user info
        admin_reply_message.reply_to_message = MagicMock()
        admin_reply_message.reply_to_message.text = (
            "📩 Сообщение от пользователя:\n\n"
            "👤 Ivan Petrov\n"
            "@ivanpetrov\n"
            f"ID: {user_id}\n"
            f"\n💬 Сообщение:\n{user_message_text}"
        )
        
        with patch('bot.handlers.settings.async_session_maker') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_session_instance
            mock_session.return_value.__aexit__ = AsyncMock()
            
            with patch('bot.handlers.settings.UserService.get_or_create_user', return_value=mock_user):
                with patch('bot.handlers.settings.settings') as mock_settings:
                    mock_settings.admin_id_list = [admin_id]
                    
                    await handle_admin_reply(admin_reply_message)
                    
                    # Verify: User receives admin's reply
                    user_reply_call = None
                    for call in mock_bot.send_message.call_args_list:
                        if call[0][0] == user_id:
                            user_reply_call = call
                            break
                    
                    assert user_reply_call is not None, "User should receive admin's reply"
                    user_reply_text = user_reply_call[0][1]
                    assert "Ответ от администратора" in user_reply_text
                    assert admin_reply_text in user_reply_text
                    
                    # Verify: Admin receives confirmation
                    admin_reply_message.reply.assert_called_once()
                    confirmation_text = admin_reply_message.reply.call_args[0][0]
                    assert "Ответ отправлен пользователю" in confirmation_text or "✅" in confirmation_text


    @pytest.mark.asyncio
    async def test_non_admin_reply_is_ignored(self):
        """Test that regular users cannot use the reply handler"""
        regular_user_id = 12345
        
        # Mock message from regular user trying to reply
        mock_message = AsyncMock(spec=Message)
        mock_message.from_user = MagicMock(spec=User)
        mock_message.from_user.id = regular_user_id
        mock_message.text = "Some reply"
        mock_message.reply_to_message = MagicMock()
        mock_message.reply_to_message.text = "Some message"
        mock_message.bot = AsyncMock()
        
        with patch('bot.handlers.settings.settings') as mock_settings:
            mock_settings.admin_id_list = [99999]  # Different from regular_user_id
            
            await handle_admin_reply(mock_message)
            
            # Verify: No message is sent (handler returns early)
            assert not mock_message.bot.send_message.called


    @pytest.mark.asyncio
    async def test_multiple_admins_receive_message(self):
        """Test that support message is sent to all configured admins"""
        user_id = 12345
        admin_ids = [99999, 88888, 77777]
        
        mock_user = MagicMock()
        mock_user.telegram_id = user_id
        mock_user.first_name = "Test"
        mock_user.username = "testuser"
        mock_user.status = UserStatus.APPROVED
        mock_user.interface_language = InterfaceLanguage.RUSSIAN
        
        mock_state = AsyncMock(spec=FSMContext)
        mock_state.clear = AsyncMock()
        
        mock_message = AsyncMock(spec=Message)
        mock_message.from_user = MagicMock(spec=User)
        mock_message.from_user.id = user_id
        mock_message.text = "Test support message"
        mock_message.answer = AsyncMock()
        mock_message.copy_to = AsyncMock()
        mock_message.bot = AsyncMock()
        mock_message.bot.send_message = AsyncMock(return_value=MagicMock(message_id=1001))
        
        with patch('bot.handlers.settings.async_session_maker') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_session_instance
            mock_session.return_value.__aexit__ = AsyncMock()
            
            with patch('bot.handlers.settings.UserService.get_or_create_user', return_value=mock_user):
                with patch('bot.handlers.settings.settings') as mock_settings:
                    mock_settings.admin_id_list = admin_ids
                    
                    await receive_support_message(mock_message, mock_state)
                    
                    # Verify: Message sent to all admins
                    sent_to_admins = set()
                    for call in mock_message.bot.send_message.call_args_list:
                        recipient_id = call[0][0]
                        if recipient_id in admin_ids:
                            sent_to_admins.add(recipient_id)
                    
                    assert len(sent_to_admins) == len(admin_ids), \
                        f"Message should be sent to all {len(admin_ids)} admins"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
