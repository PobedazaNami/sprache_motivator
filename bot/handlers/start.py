from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
## Removed SQLAlchemy AsyncSession (migrated to MongoDB)

from bot.models.database import UserStatus, InterfaceLanguage, async_session_maker
from bot.services.database_service import UserService
from bot.locales.texts import get_text
from bot.utils.keyboards import get_language_selection_keyboard, get_main_menu_keyboard
from bot.config import settings


router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Handle /start command"""
    # Clear any active state
    await state.clear()
    
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(
            session,
            message.from_user.id,
            message.from_user.username,
            message.from_user.first_name,
            message.from_user.last_name
        )
        # Auto-approve on /start if this user is an admin but still pending
        if user.status == UserStatus.PENDING and message.from_user.id in settings.admin_id_list:
            await UserService.update_user(session, user, status=UserStatus.APPROVED)

        # If user is new or pending (non-admin), show language selection
        if user.status == UserStatus.PENDING:
            # Get user's name (username or first name)
            user_name = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name or "друже"
            welcome_text = f"👋 Вітаємо, {user_name}, в Sprache Motivator!\n\nОберіть мову інтерфейсу:"
            await message.answer(
                welcome_text,
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
        
        # If admin, approve immediately
        if callback.from_user.id in settings.admin_id_list:
            await UserService.update_user(
                session, 
                user, 
                interface_language=interface_lang,
                status=UserStatus.APPROVED
            )
        else:
            # Regular user - just update language
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


@router.message(F.text.in_([
    "🔙 Главное меню", "🔙 Головне меню"
]))
async def show_main_menu(message: Message, state: FSMContext):
    """Return to main menu and clear state"""
    # Clear any active state
    await state.clear()
    
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, message.from_user.id)
        
        if user.status != UserStatus.APPROVED:
            return
        
        lang = user.interface_language.value
        await message.answer(
            get_text(lang, "main_menu"),
            reply_markup=get_main_menu_keyboard(user)
        )

