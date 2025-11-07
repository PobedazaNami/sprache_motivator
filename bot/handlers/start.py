from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.database import UserStatus, InterfaceLanguage, async_session_maker
from bot.services.database_service import UserService
from bot.locales.texts import get_text
from bot.utils.keyboards import get_language_selection_keyboard, get_main_menu_keyboard
from bot.config import settings


router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    """Handle /start command"""
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(
            session,
            message.from_user.id,
            message.from_user.username,
            message.from_user.first_name,
            message.from_user.last_name
        )
        
        # If user is new or pending, show language selection
        if user.status == UserStatus.PENDING:
            await message.answer(
                get_text("ru", "welcome"),
                reply_markup=get_language_selection_keyboard()
            )
        elif user.status == UserStatus.REJECTED:
            lang = user.interface_language.value
            await message.answer(get_text(lang, "rejected"))
        else:
            # Approved user - show main menu
            lang = user.interface_language.value
            await message.answer(
                get_text(lang, "main_menu"),
                reply_markup=get_main_menu_keyboard(user)
            )


@router.callback_query(F.data.startswith("lang_"))
async def select_language(callback: CallbackQuery):
    """Handle language selection"""
    lang_code = callback.data.split("_")[1]
    
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(
            session,
            callback.from_user.id
        )
        
        # Update interface language
        interface_lang = InterfaceLanguage.UKRAINIAN if lang_code == "uk" else InterfaceLanguage.RUSSIAN
        await UserService.update_user(session, user, interface_language=interface_lang)
        
        # Show pending approval message or main menu
        if user.status == UserStatus.PENDING:
            await callback.message.edit_text(
                get_text(lang_code, "pending_approval")
            )
            
            # Notify admins about new user
            admin_text = f"🆕 New user registration:\n\n"
            admin_text += f"Name: {user.first_name or ''} {user.last_name or ''}\n"
            admin_text += f"Username: @{user.username or 'N/A'}\n"
            admin_text += f"Telegram ID: {user.telegram_id}\n"
            
            from bot.utils.keyboards import get_user_approval_keyboard
            
            for admin_id in settings.admin_id_list:
                try:
                    await callback.bot.send_message(
                        admin_id,
                        admin_text,
                        reply_markup=get_user_approval_keyboard(user.id)
                    )
                except Exception:
                    pass
        else:
            await callback.message.edit_text(
                get_text(lang_code, "main_menu")
            )
            await callback.message.answer(
                get_text(lang_code, "main_menu"),
                reply_markup=get_main_menu_keyboard(user)
            )
    
    await callback.answer()
