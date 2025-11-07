from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from bot.models.database import UserStatus, InterfaceLanguage, async_session_maker
from bot.services.database_service import UserService, BroadcastService
from bot.locales.texts import get_text
from bot.utils.keyboards import (
    get_admin_menu_keyboard,
    get_user_approval_keyboard,
    get_broadcast_confirm_keyboard,
    get_main_menu_keyboard
)
from bot.config import settings


router = Router()


class BroadcastStates(StatesGroup):
    waiting_for_message = State()
    confirming = State()


def is_admin(user_id: int) -> bool:
    """Check if user is admin"""
    return user_id in settings.admin_id_list


@router.message(Command("admin"))
async def admin_menu(message: Message):
    """Show admin menu"""
    if not is_admin(message.from_user.id):
        return
    
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, message.from_user.id)
        lang = user.interface_language.value if user.interface_language else InterfaceLanguage.RUSSIAN.value
        
        await message.answer(
            get_text(lang, "admin_menu"),
            reply_markup=get_admin_menu_keyboard(lang)
        )


@router.message(F.text.in_([
    "👥 Пользователи на проверке", "👥 Користувачі на перевірці"
]))
async def show_pending_users(message: Message):
    """Show pending users for approval"""
    if not is_admin(message.from_user.id):
        return
    
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, message.from_user.id)
        lang = user.interface_language.value
        
        pending_users = await UserService.get_pending_users(session)
        
        if not pending_users:
            await message.answer(get_text(lang, "no_pending_users"))
            return
        
        text = get_text(lang, "pending_users")
        
        for pending_user in pending_users:
            user_info = f"\n👤 {pending_user.first_name or ''} {pending_user.last_name or ''}\n"
            user_info += f"@{pending_user.username or 'N/A'}\n"
            user_info += f"ID: {pending_user.telegram_id}\n"
            
            await message.answer(
                user_info,
                reply_markup=get_user_approval_keyboard(pending_user.id)
            )


@router.callback_query(F.data.startswith("approve_"))
async def approve_user(callback: CallbackQuery):
    """Approve a user"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Not authorized", show_alert=True)
        return
    
    user_id = int(callback.data.split("_")[1])
    
    async with async_session_maker() as session:
        admin = await UserService.get_or_create_user(session, callback.from_user.id)
        lang = admin.interface_language.value
        
        # Get user to approve
        from sqlalchemy import select
        from bot.models.database import User
        
        result = await session.execute(select(User).where(User.id == user_id))
        user_to_approve = result.scalar_one_or_none()
        
        if user_to_approve:
            await UserService.update_user(session, user_to_approve, status=UserStatus.APPROVED)
            
            # Notify user
            user_lang = user_to_approve.interface_language.value
            try:
                await callback.bot.send_message(
                    user_to_approve.telegram_id,
                    get_text(user_lang, "main_menu"),
                    reply_markup=get_main_menu_keyboard(user_to_approve)
                )
            except Exception:
                pass
            
            await callback.message.edit_text(get_text(lang, "user_approved"))
    
    await callback.answer()


@router.callback_query(F.data.startswith("reject_"))
async def reject_user(callback: CallbackQuery):
    """Reject a user"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Not authorized", show_alert=True)
        return
    
    user_id = int(callback.data.split("_")[1])
    
    async with async_session_maker() as session:
        admin = await UserService.get_or_create_user(session, callback.from_user.id)
        lang = admin.interface_language.value
        
        # Get user to reject
        from sqlalchemy import select
        from bot.models.database import User
        
        result = await session.execute(select(User).where(User.id == user_id))
        user_to_reject = result.scalar_one_or_none()
        
        if user_to_reject:
            await UserService.update_user(session, user_to_reject, status=UserStatus.REJECTED)
            
            # Notify user
            user_lang = user_to_reject.interface_language.value
            try:
                await callback.bot.send_message(
                    user_to_reject.telegram_id,
                    get_text(user_lang, "rejected")
                )
            except Exception:
                pass
            
            await callback.message.edit_text(get_text(lang, "user_rejected"))
    
    await callback.answer()


@router.message(F.text.in_([
    "📊 Статистика пользователей", "📊 Статистика користувачів"
]))
async def show_user_stats(message: Message):
    """Show user statistics"""
    if not is_admin(message.from_user.id):
        return
    
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, message.from_user.id)
        lang = user.interface_language.value
        
        stats = await UserService.get_user_stats(session)
        
        await message.answer(
            get_text(lang, "total_users",
                    total=stats["total"],
                    approved=stats["approved"],
                    pending=stats["pending"],
                    rejected=stats["rejected"])
        )


@router.message(F.text.in_([
    "📢 Рассылка", "📢 Розсилка"
]))
async def start_broadcast(message: Message, state: FSMContext):
    """Start broadcast creation"""
    if not is_admin(message.from_user.id):
        return
    
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, message.from_user.id)
        lang = user.interface_language.value
        
        await message.answer(get_text(lang, "broadcast_prompt"))
        await state.set_state(BroadcastStates.waiting_for_message)
        await state.update_data(lang=lang, admin_id=message.from_user.id)


@router.message(BroadcastStates.waiting_for_message)
async def receive_broadcast_message(message: Message, state: FSMContext):
    """Receive broadcast message"""
    data = await state.get_data()
    lang = data.get("lang", "ru")
    
    async with async_session_maker() as session:
        recipients = await UserService.get_broadcast_recipients(session)
        count = len(recipients)
        
        await message.answer(
            get_text(lang, "broadcast_confirm", count=count),
            reply_markup=get_broadcast_confirm_keyboard()
        )
        
        await state.update_data(message_text=message.text, recipients_count=count)
        await state.set_state(BroadcastStates.confirming)


@router.callback_query(F.data == "broadcast_confirm_yes", BroadcastStates.confirming)
async def confirm_broadcast(callback: CallbackQuery, state: FSMContext):
    """Confirm and send broadcast"""
    data = await state.get_data()
    lang = data.get("lang", "ru")
    message_text = data.get("message_text")
    admin_id = data.get("admin_id")
    
    await callback.message.edit_text(get_text(lang, "broadcast_started"))
    
    async with async_session_maker() as session:
        # Create broadcast record
        broadcast = await BroadcastService.create_broadcast(session, message_text, admin_id)
        
        # Get recipients
        recipients = await UserService.get_broadcast_recipients(session)
        
        sent = 0
        failed = 0
        
        for recipient in recipients:
            try:
                await callback.bot.send_message(recipient.telegram_id, message_text)
                sent += 1
            except Exception:
                failed += 1
        
        # Update broadcast record
        await BroadcastService.update_broadcast(session, broadcast.id, sent, failed, True)
        
        await callback.message.answer(
            get_text(lang, "broadcast_completed", sent=sent, failed=failed)
        )
    
    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "broadcast_confirm_no", BroadcastStates.confirming)
async def cancel_broadcast(callback: CallbackQuery, state: FSMContext):
    """Cancel broadcast"""
    await callback.message.edit_text("❌ Broadcast cancelled")
    await state.clear()
    await callback.answer()


@router.message(F.text.in_([
    "🏆 Рейтинг активности", "🏆 Рейтинг активності"
]))
async def show_user_rating(message: Message):
    """Show user activity rating"""
    if not is_admin(message.from_user.id):
        return
    
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, message.from_user.id)
        lang = user.interface_language.value
        
        top_users = await UserService.get_top_users(session, 10)
        
        text = get_text(lang, "user_rating")
        
        for i, top_user in enumerate(top_users, 1):
            text += f"\n{i}. {top_user.first_name or ''} {top_user.last_name or ''}"
            text += f" (@{top_user.username or 'N/A'})"
            text += f" - {top_user.activity_score} pts"
        
        await message.answer(text)


@router.message(F.text.in_([
    "⬅️ Назад"
]))
async def back_to_main(message: Message):
    """Go back to main menu"""
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, message.from_user.id)
        
        if user.status != UserStatus.APPROVED:
            return
        
        lang = user.interface_language.value
        await message.answer(
            get_text(lang, "main_menu"),
            reply_markup=get_main_menu_keyboard(user)
        )
