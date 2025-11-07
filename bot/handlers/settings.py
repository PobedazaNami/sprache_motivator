from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

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
async def settings_menu(message: Message):
    """Show settings menu"""
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, message.from_user.id)
        
        if user.status != UserStatus.APPROVED:
            return
        
        lang = user.interface_language.value
        
        text = get_text(lang, "settings_menu")
        text += f"\n• {get_text(lang, 'interface_lang')}: {user.interface_language.value.upper()}"
        text += f"\n• {get_text(lang, 'learning_lang')}: {user.learning_language.value.upper()}"
        text += f"\n• {get_text(lang, 'difficulty')}: {user.difficulty_level.value if user.difficulty_level else 'A2'}"
        
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
    """Show difficulty selection"""
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, callback.from_user.id)
        lang = user.interface_language.value
        
        await callback.message.edit_text(
            get_text(lang, "select_difficulty"),
            reply_markup=get_difficulty_keyboard(lang)
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
        
        lang = user.interface_language.value
        
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
    """Update difficulty level"""
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
        
        await callback.message.edit_text(get_text(lang, "settings_updated"))
    
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
