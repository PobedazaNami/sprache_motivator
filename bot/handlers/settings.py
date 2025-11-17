from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from bot.models.database import UserStatus, InterfaceLanguage, LearningLanguage, DifficultyLevel, async_session_maker
from bot.services.database_service import UserService
from bot.locales.texts import get_text
from bot.utils.keyboards import (
    get_settings_keyboard,
    get_interface_language_keyboard,
    get_learning_language_keyboard,
    get_difficulty_keyboard,
    get_main_menu_keyboard
)


router = Router()


@router.message(F.text.in_([
    "⚙️ Настройки", "⚙️ Налаштування"
]))
async def settings_menu(message: Message, state: FSMContext):
    """Show settings menu"""
    # Clear any previous state
    await state.clear()
    
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, message.from_user.id)
        
        if user.status != UserStatus.APPROVED:
            return
        
        lang = user.interface_language.value
        
        text = get_text(lang, "settings_menu")
        text += f"\n• {get_text(lang, 'interface_lang')}: {user.interface_language.value.upper()}"
        text += f"\n• {get_text(lang, 'learning_lang')}: {user.learning_language.value.upper()}"
        # Difficulty level removed - now handled through topic selection in trainer settings
        
        # Add trial/subscription status
        text += "\n\n"
        if user.subscription_active:
            # Check if unlimited or time-limited subscription
            days_remaining = UserService.get_trial_days_remaining(user)
            if days_remaining == 999:
                # Unlimited subscription
                status = "♾️ Безлімітна підписка" if lang == "uk" else "♾️ Безлимитная подписка"
            else:
                # Time-limited subscription with days remaining
                days_word = "днів" if lang == "uk" else "дней"
                status = f"✅ Підписка: {days_remaining} {days_word} залишилось" if lang == "uk" else f"✅ Подписка: {days_remaining} {days_word} осталось"
        elif user.trial_activated:
            days_remaining = UserService.get_trial_days_remaining(user)
            if days_remaining > 0:
                days_word = "днів" if lang == "uk" else "дней"
                status = f"🎁 Пробний: {days_remaining} {days_word} залишилось" if lang == "uk" else f"🎁 Пробный: {days_remaining} {days_word} осталось"
            else:
                status = "⏰ Пробний період закінчився" if lang == "uk" else "⏰ Пробный период закончился"
        else:
            status = "⚠️ Пробний період не активовано" if lang == "uk" else "⚠️ Пробный период не активирован"
        
        text += get_text(lang, "trial_status", status=status)
        
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
async def support_message(message: Message):
    """Show support contact"""
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, message.from_user.id)
        
        if user.status != UserStatus.APPROVED:
            return
        
        lang = user.interface_language.value
        await message.answer(get_text(lang, "support_message"))
