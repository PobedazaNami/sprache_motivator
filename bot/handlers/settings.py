from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from bot.models.database import UserStatus, InterfaceLanguage, LearningLanguage, DifficultyLevel, async_session_maker
from bot.services.database_service import UserService
from bot.locales.texts import get_text
from bot.utils.keyboards import (
    get_settings_keyboard,
    get_interface_language_keyboard,
    get_learning_language_keyboard,
    get_difficulty_keyboard,
    get_main_menu_keyboard,
    get_cancel_keyboard
)
from bot.config import settings


router = Router()


class SupportStates(StatesGroup):
    waiting_for_message = State()


@router.message(F.text.in_([
    "⚙️ Настройки", "⚙️ Налаштування"
]))
async def settings_menu(message: Message, state: FSMContext):
    """Show settings menu"""
    # Clear any previous state (FSM and Redis)
    await state.clear()
    from bot.services.redis_service import redis_service
    await redis_service.clear_user_state(message.from_user.id)
    
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, message.from_user.id)
        
        if user.status != UserStatus.APPROVED:
            return
        
        lang = user.interface_language.value
        
        text = get_text(lang, "settings_menu")
        text += f"\n• {get_text(lang, 'interface_lang')}: {user.interface_language.value.upper()}"
        text += f"\n• {get_text(lang, 'learning_lang')}: {user.learning_language.value.upper()}"
        # Difficulty level removed - now handled through topic selection in trainer settings
        
        # Add subscription status
        text += "\n\n"
        if user.subscription_active:
            # User has active subscription - check if unlimited or time-limited
            if user.subscription_until is None:
                # Unlimited subscription (subscription_active=True with no expiration date, typically for admins)
                status = "♾️ Безлімітна підписка для перекладача" if lang == "uk" else "♾️ Безлимитная подписка для переводчика"
            else:
                # Time-limited subscription with expiration date
                from datetime import datetime
                import pytz
                berlin_tz = pytz.timezone('Europe/Berlin')
                now = datetime.now(berlin_tz)
                if isinstance(user.subscription_until, datetime):
                    subscription_until_aware = user.subscription_until.replace(tzinfo=pytz.UTC).astimezone(berlin_tz)
                    days_remaining = (subscription_until_aware - now).days
                    days_word = "днів" if lang == "uk" else "дней"
                    status = f"✅ Підписка на перекладач: {days_remaining} {days_word}" if lang == "uk" else f"✅ Подписка на переводчик: {days_remaining} {days_word}"
                else:
                    status = "✅ Активна підписка на перекладач" if lang == "uk" else "✅ Активная подписка на переводчик"
        else:
            status = "📖 Перекладач: потрібна підписка €4/міс\n🎯 Тренажер: безкоштовно!" if lang == "uk" else "📖 Переводчик: требуется подписка €4/мес\n🎯 Тренажёр: бесплатно!"
        
        text += get_text(lang, "subscription_status", status=status)
        
        await message.answer(text, reply_markup=get_settings_keyboard(lang))


@router.callback_query(F.data == "settings_interface_lang")
async def select_interface_lang(callback: CallbackQuery):
    """Show interface language selection"""
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, callback.from_user.id)
        lang = user.interface_language.value
        
        await callback.message.edit_text(
            get_text(lang, "select_interface_lang"),
            reply_markup=get_interface_language_keyboard()
        )
    
    await callback.answer()


@router.callback_query(F.data == "settings_learning_lang")
async def select_learning_lang(callback: CallbackQuery):
    """Show learning language selection"""
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, callback.from_user.id)
        lang = user.interface_language.value
        
        await callback.message.edit_text(
            get_text(lang, "select_learning_lang"),
            reply_markup=get_learning_language_keyboard(lang)
        )
    
    await callback.answer()


@router.callback_query(F.data == "settings_difficulty")
async def select_difficulty(callback: CallbackQuery):
    """Show difficulty selection - redirects to trainer topic selection"""
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, callback.from_user.id)
        lang = user.interface_language.value
        
        # Difficulty is now handled through topic selection in trainer settings
        redirect_msg = "⚠️ Рівень складності тепер налаштовується через вибір теми в тренажері." if lang == "uk" else "⚠️ Уровень сложности теперь настраивается через выбор темы в тренажере."
        
        await callback.message.edit_text(
            redirect_msg,
            reply_markup=get_settings_keyboard(lang)
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("set_interface_"))
async def update_interface_lang(callback: CallbackQuery):
    """Update interface language"""
    lang_code = callback.data.split("_")[2]
    interface_lang = InterfaceLanguage.UKRAINIAN if lang_code == "uk" else InterfaceLanguage.RUSSIAN
    
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, callback.from_user.id)
        await UserService.update_user(session, user, interface_language=interface_lang)
        
        # Use the new language code for messages
        lang = lang_code
        
        await callback.message.edit_text(get_text(lang, "settings_updated"))
        
        # Show updated main menu
        await callback.message.answer(
            get_text(lang, "main_menu"),
            reply_markup=get_main_menu_keyboard(user)
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("set_learning_"))
async def update_learning_lang(callback: CallbackQuery):
    """Update learning language"""
    lang_code = callback.data.split("_")[2]
    learning_lang = LearningLanguage.ENGLISH if lang_code == "en" else LearningLanguage.GERMAN
    
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, callback.from_user.id)
        await UserService.update_user(session, user, learning_language=learning_lang)
        
        lang = user.interface_language.value
        
        await callback.message.edit_text(get_text(lang, "settings_updated"))
    
    await callback.answer()


@router.callback_query(F.data.startswith("set_difficulty_"))
async def update_difficulty(callback: CallbackQuery):
    """Update difficulty level - kept for backward compatibility"""
    difficulty_code = callback.data.split("_")[2]
    difficulty_map = {
        "A2": DifficultyLevel.A2,
        "B1": DifficultyLevel.B1,
        "B2": DifficultyLevel.B2,
        "A2-B2": DifficultyLevel.COMBINED
    }
    difficulty = difficulty_map.get(difficulty_code, DifficultyLevel.A2)
    
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, callback.from_user.id)
        await UserService.update_user(session, user, difficulty_level=difficulty)
        
        lang = user.interface_language.value
        
        # Notify that difficulty is now handled through topic selection
        msg = get_text(lang, "settings_updated") + "\n\n" + (
            "💡 Підказка: Рівень складності тепер налаштовується через вибір теми в тренажері." 
            if lang == "uk" else 
            "💡 Подсказка: Уровень сложности теперь настраивается через выбор темы в тренажере."
        )
        await callback.message.edit_text(msg)
    
    await callback.answer()


@router.callback_query(F.data == "settings_back")
async def settings_back(callback: CallbackQuery):
    """Go back from settings"""
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, callback.from_user.id)
        lang = user.interface_language.value
        
        await callback.message.delete()
        await callback.message.answer(
            get_text(lang, "main_menu"),
            reply_markup=get_main_menu_keyboard(user)
        )
    
    await callback.answer()


@router.message(F.text.in_([
    "💬 Техподдержка", "💬 Техпідтримка"
]))
async def support_message(message: Message, state: FSMContext):
    """Start support conversation"""
    # Clear any previous state (FSM and Redis)
    await state.clear()
    from bot.services.redis_service import redis_service
    await redis_service.clear_user_state(message.from_user.id)
    
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, message.from_user.id)
        
        if user.status != UserStatus.APPROVED:
            return
        
        lang = user.interface_language.value
        await message.answer(
            get_text(lang, "support_prompt"),
            reply_markup=get_cancel_keyboard(lang)
        )
        await state.set_state(SupportStates.waiting_for_message)


@router.message(SupportStates.waiting_for_message)
async def receive_support_message(message: Message, state: FSMContext):
    """Receive and forward user's support message to admins"""
    # Allow user to cancel with back button
    if message.text in ["🔙 Главное меню", "🔙 Головне меню", "❌ Скасувати", "❌ Отменить"]:
        await state.clear()
        async with async_session_maker() as session:
            user = await UserService.get_or_create_user(session, message.from_user.id)
            lang = user.interface_language.value
            await message.answer(
                get_text(lang, "main_menu"),
                reply_markup=get_main_menu_keyboard(user)
            )
        return
    
    # Check if user has an active training session - training takes priority
    from bot.services.redis_service import redis_service
    import time
    
    training_state = await redis_service.get_user_state(message.from_user.id)
    if training_state:
        state_type = training_state.get("state")
        if state_type in ["awaiting_training_answer", "awaiting_express_answer"]:
            state_timestamp = training_state.get("timestamp", 0)
            current_time = time.time()
            state_age_minutes = (current_time - state_timestamp) / 60
            
            if state_age_minutes < 10:
                # User has active training session - route to appropriate handler
                await state.clear()  # Clear support state
                if state_type == "awaiting_training_answer":
                    from bot.handlers.trainer import check_training_answer
                    await check_training_answer(message, state)
                else:
                    from bot.handlers.express_trainer import check_express_answer
                    await check_express_answer(message, state)
                return
            else:
                # Stale training state - clear it
                await redis_service.clear_user_state(message.from_user.id)
    
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, message.from_user.id)
        lang = user.interface_language.value
        
        # Confirm receipt to user
        await message.answer(get_text(lang, "support_message_sent"))
        
        # Show main menu again
        await message.answer(
            get_text(lang, "main_menu"),
            reply_markup=get_main_menu_keyboard(user)
        )
        
        # Forward to admins with user context
        user_info = f"📩 Повідомлення від користувача:\n\n" if lang == "uk" else f"📩 Сообщение от пользователя:\n\n"
        user_info += f"👤 {user.first_name or ''} {user.last_name or ''}\n"
        user_info += f"@{user.username or 'N/A'}\n"
        user_info += f"ID: {user.telegram_id}\n"
        user_info += f"\n💬 Повідомлення:\n{message.text}" if lang == "uk" else f"\n💬 Сообщение:\n{message.text}"
        
        for admin_id in settings.admin_id_list:
            try:
                # Send user info and forward the actual message
                sent_msg = await message.bot.send_message(
                    admin_id,
                    user_info
                )
                # Copy the message so admin can reply to it
                await message.copy_to(admin_id, reply_to_message_id=sent_msg.message_id)
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Failed to forward support message to admin {admin_id}: {e}")
    
    await state.clear()


@router.message(F.reply_to_message)
async def handle_admin_reply(message: Message):
    """Handle admin replies to user support messages"""
    # Check if sender is admin
    if message.from_user.id not in settings.admin_id_list:
        return
    
    # Get the original message that admin is replying to
    replied_to = message.reply_to_message
    if not replied_to or not replied_to.text:
        return
    
    # Extract user ID from the replied message
    # The format is: "ID: {telegram_id}"
    try:
        lines = replied_to.text.split('\n')
        user_id = None
        for line in lines:
            if line.startswith('ID:'):
                user_id = int(line.split(':')[1].strip())
                break
        
        if not user_id:
            return
        
        # Get user to know their language
        async with async_session_maker() as session:
            user = await UserService.get_or_create_user(session, user_id)
            lang = user.interface_language.value
            
            # Send admin's reply to user
            admin_reply = f"📬 {get_text(lang, 'support_admin_reply')}\n\n{message.text}"
            await message.bot.send_message(user_id, admin_reply)
            
            # Confirm to admin
            await message.reply("✅ Відповідь надіслано користувачу" if lang == "uk" else "✅ Ответ отправлен пользователю")
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to handle admin reply: {e}")
        await message.reply("❌ Помилка при надсиланні відповіді" if message.from_user.id else "❌ Ошибка при отправке ответа")
