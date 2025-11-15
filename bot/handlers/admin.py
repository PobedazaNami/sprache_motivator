from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from bot.models.database import UserStatus, InterfaceLanguage, async_session_maker
from datetime import timedelta

from bot.services.database_service import UserService, BroadcastService
from bot.locales.texts import get_text
from bot.utils.keyboards import (
    get_admin_menu_keyboard,
    get_user_approval_keyboard,
    get_broadcast_confirm_keyboard,
    get_main_menu_keyboard,
    get_user_access_keyboard,
)
from bot.config import settings


router = Router()


class BroadcastStates(StatesGroup):
    waiting_for_message = State()
    confirming = State()


class AccessStates(StatesGroup):
    waiting_for_user_id = State()


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
    "🛠 Адмінка", "🛠 Админка"
]))
async def admin_menu_button(message: Message):
    """Open admin menu from main keyboard button"""
    await admin_menu(message)


@router.message(F.text.in_([
    "🔐 Керування доступом", "🔐 Управление доступом"
]))
async def admin_access_prompt(message: Message, state: FSMContext):
    """Ask admin to enter user Telegram ID for access management"""
    if not is_admin(message.from_user.id):
        return

    async with async_session_maker() as session:
        admin = await UserService.get_or_create_user(session, message.from_user.id)
        lang = admin.interface_language.value if admin.interface_language else InterfaceLanguage.RUSSIAN.value

    await message.answer(get_text(lang, "admin_access_enter_id"))
    await state.set_state(AccessStates.waiting_for_user_id)


@router.message(AccessStates.waiting_for_user_id)
async def admin_access_by_id(message: Message, state: FSMContext):
    """Handle admin input of user Telegram ID and show access buttons"""
    if not is_admin(message.from_user.id):
        await state.clear()
        return

    try:
        target_id = int(message.text.strip())
    except ValueError:
        await message.answer("Please enter a valid numeric Telegram ID.")
        return

    async with async_session_maker() as session:
        admin = await UserService.get_or_create_user(session, message.from_user.id)
        lang = admin.interface_language.value if admin.interface_language else InterfaceLanguage.RUSSIAN.value

        target_user = await UserService.get_or_create_user(session, target_id)
        if not target_user:
            await message.answer(get_text(lang, "admin_access_user_not_found"))
            await state.clear()
            return

        # Build human-readable status
        from bot.services.database_service import UserService as USvc

        # Status text
        if target_user.status == UserStatus.APPROVED:
            status_text = "approved" if lang == "en" else ("підтверджено" if lang == "uk" else "подтверждён")
        elif target_user.status == UserStatus.PENDING:
            status_text = "pending" if lang == "en" else ("очікує" if lang == "uk" else "ожидает")
        else:
            status_text = "rejected" if lang == "en" else ("відхилено" if lang == "uk" else "отклонён")

        # Trial text
        if not target_user.trial_activated:
            trial_text = "не активований" if lang == "uk" else "не активирован"
        else:
            days_left = USvc.get_trial_days_remaining(target_user)
            if days_left >= 999:
                trial_text = "не актуальний (є безлімітна підписка)" if lang == "uk" else "не актуален (есть безлимитная подписка)"
            else:
                unit = "днів" if lang == "uk" else "дней"
                trial_text = f"активний, залишилось {days_left} {unit}" if lang == "uk" else f"активен, осталось {days_left} {unit}"

        # Subscription text
        if target_user.subscription_active:
            if target_user.subscription_until:
                until_str = target_user.subscription_until.strftime("%Y-%m-%d")
                subscription_text = (
                    f"активна до {until_str}" if lang == "uk" else f"активна до {until_str}"
                )
            else:
                subscription_text = (
                    "безлімітна (без кінцевої дати)" if lang == "uk" else "безлимитная (без конечной даты)"
                )
        else:
            subscription_text = "відсутня" if lang == "uk" else "отсутствует"

        header = get_text(lang, "admin_access_user_header", user_id=target_user.telegram_id)
        status_block = get_text(
            lang,
            "admin_access_status",
            status=status_text,
            trial=trial_text,
            subscription=subscription_text,
        )

        await message.answer(
            header + status_block,
            reply_markup=get_user_access_keyboard(target_user.telegram_id),
        )

    await state.clear()


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
        
        # Get user to approve (Mongo)
        user_to_approve = await UserService.get_or_create_user(session, user_id)
        if user_to_approve.status != UserStatus.APPROVED:
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


@router.callback_query(F.data.startswith("access_"))
async def manage_user_access(callback: CallbackQuery):
    """Manage user access: trial, 30 days, unlimited"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Not authorized", show_alert=True)
        return

    # data format: access_<type>_<telegram_id>
    parts = callback.data.split("_")
    if len(parts) < 3:
        await callback.answer("Invalid data", show_alert=True)
        return

    access_type = parts[1]
    user_id = int(parts[2])

    async with async_session_maker() as session:
        admin = await UserService.get_or_create_user(session, callback.from_user.id)
        lang = admin.interface_language.value

        user = await UserService.get_or_create_user(session, user_id)

        # Base: user must be approved to manage access
        if user.status != UserStatus.APPROVED:
            await UserService.update_user(session, user, status=UserStatus.APPROVED)

        from bot.services.database_service import _now

        if access_type == "trial":
            # Activate (or re-activate) 10-day trial from now
            user.trial_activated = True
            user.trial_activation_date = _now()
            # Trial only, no subscription
            user.subscription_active = False
            user.subscription_until = None
            await UserService.update_user(
                session,
                user,
                trial_activated=True,
                trial_activation_date=user.trial_activation_date,
                subscription_active=False,
                subscription_until=None,
            )
            text_key = "admin_access_trial_set"

        elif access_type == "30":
            # 30-day subscription from now
            now = _now()
            user.subscription_active = True
            user.subscription_until = now + timedelta(days=30)
            await UserService.update_user(
                session,
                user,
                subscription_active=True,
                subscription_until=user.subscription_until,
            )
            text_key = "admin_access_30_set"

        elif access_type == "unlimited":
            # Unlimited subscription
            user.subscription_active = True
            user.subscription_until = None
            await UserService.update_user(
                session,
                user,
                subscription_active=True,
                subscription_until=None,
            )
            text_key = "admin_access_unlimited_set"
        else:
            await callback.answer("Unknown access type", show_alert=True)
            return

        # Notify admin in chat
        await callback.message.answer(
            get_text(
                lang,
                text_key,
                user_id=user.telegram_id,
            )
        )

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
        
        # Get user to reject (Mongo)
        user_to_reject = await UserService.get_or_create_user(session, user_id)
        if user_to_reject.status != UserStatus.REJECTED:
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
