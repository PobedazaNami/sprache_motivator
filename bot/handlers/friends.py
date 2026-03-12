from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from bot.models.database import UserStatus, async_session_maker
from bot.services.database_service import UserService
from bot.services import mongo_service
from bot.locales.texts import get_text
from bot.utils.keyboards import get_friends_menu_keyboard, get_friend_list_keyboard, get_pending_requests_keyboard


router = Router()


class FriendsStates(StatesGroup):
    """FSM states for friends management"""
    waiting_for_friend_id = State()


def _friend_display_name(friend, friend_id: int) -> tuple[str, str]:
    friend_name = friend.first_name or friend.username or f"User {friend_id}"
    friend_username = friend.username or str(friend_id)
    return friend_name, friend_username


def _build_friend_stats_text(lang: str, friend_name: str, friend_username: str, stats: dict, streak: int) -> str:
    completed = stats.get("completed", 0)
    quality = stats.get("quality", 0)
    know = stats.get("flashcard_know", 0)
    retry = stats.get("flashcard_retry", 0)
    is_active_today = completed > 0 or know > 0 or retry > 0

    if not is_active_today:
        return get_text(
            lang,
            "friends_stats_user_inactive",
            name=friend_name,
            username=friend_username,
            streak=streak,
        )

    quality_line = ""
    if completed > 0:
        quality_line = get_text(lang, "friends_stats_quality_inline", quality=quality)

    return get_text(
        lang,
        "friends_stats_user_active",
        name=friend_name,
        username=friend_username,
        completed=completed,
        know=know,
        retry=retry,
        quality_line=quality_line,
        streak=streak,
    )


@router.message(F.text.in_([
    "👥 Друзья", "👥 Друзі"
]))
async def friends_menu(message: Message, state: FSMContext):
    """Show friends menu"""
    # Clear any previous state (FSM and Redis)
    await state.clear()
    mongo_service.db()  # Ensure mongo is ready
    from bot.services.redis_service import redis_service
    await redis_service.clear_user_state(message.from_user.id)
    
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, message.from_user.id)
        
        if user.status != UserStatus.APPROVED:
            return
        
        # Friends feature is free for all approved users
        lang = user.interface_language.value
        
        # Get friends list
        friend_ids = await mongo_service.get_friends(message.from_user.id)
        
        if friend_ids:
            # Get friend details
            friends_list = []
            for friend_id in friend_ids:
                friend = await UserService.get_or_create_user(session, friend_id)
                friend_name, friend_username = _friend_display_name(friend, friend_id)
                friends_list.append(f"👤 {friend_name} (@{friend_username})")
            
            text = get_text(lang, "friends_list", friends_list="\n".join(friends_list))
        else:
            text = get_text(lang, "no_friends")
        
        await message.answer(
            get_text(lang, "friends_menu") + "\n\n" + text,
            reply_markup=get_friends_menu_keyboard(lang)
        )


@router.callback_query(F.data == "friends_menu")
async def friends_menu_callback(callback: CallbackQuery, state: FSMContext):
    """Show friends menu from callback"""
    await state.clear()
    
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, callback.from_user.id)
        lang = user.interface_language.value
        
        # Get friends list
        friend_ids = await mongo_service.get_friends(callback.from_user.id)
        
        if friend_ids:
            # Get friend details
            friends_list = []
            for friend_id in friend_ids:
                friend = await UserService.get_or_create_user(session, friend_id)
                friend_name, friend_username = _friend_display_name(friend, friend_id)
                friends_list.append(f"👤 {friend_name} (@{friend_username})")
            
            text = get_text(lang, "friends_list", friends_list="\n".join(friends_list))
        else:
            text = get_text(lang, "no_friends")
        
        await callback.message.edit_text(
            get_text(lang, "friends_menu") + "\n\n" + text,
            reply_markup=get_friends_menu_keyboard(lang)
        )
    
    await callback.answer()


@router.callback_query(F.data == "friends_add")
async def add_friend_prompt(callback: CallbackQuery, state: FSMContext):
    """Prompt for friend ID to add"""
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, callback.from_user.id)
        lang = user.interface_language.value
        
        await callback.message.edit_text(get_text(lang, "add_friend_prompt"))
        await state.set_state(FriendsStates.waiting_for_friend_id)
    
    await callback.answer()


@router.message(FriendsStates.waiting_for_friend_id)
async def process_add_friend(message: Message, state: FSMContext):
    """Process friend addition"""
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
                await state.clear()  # Clear friends state
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
        
        # Parse friend identifier (ID or username)
        friend_identifier = message.text.strip()
        
        # Try to parse as ID or username
        friend = None
        friend_id = None
        
        if friend_identifier.startswith("@"):
            # Username provided
            username = friend_identifier[1:]
            # Search for user by username
            friend = await UserService.get_user_by_username(session, username)
            if not friend:
                await message.answer(
                    get_text(lang, "friend_not_found"),
                    reply_markup=get_friends_menu_keyboard(lang)
                )
                await state.clear()
                return
            friend_id = friend.telegram_id
        else:
            # Try to parse as numeric ID
            try:
                friend_id = int(friend_identifier)
            except ValueError:
                await message.answer(
                    get_text(lang, "friend_not_found"),
                    reply_markup=get_friends_menu_keyboard(lang)
                )
                await state.clear()
                return
        
        # Check if trying to add self
        if friend_id == message.from_user.id:
            await message.answer(
                get_text(lang, "cannot_add_self"),
                reply_markup=get_friends_menu_keyboard(lang)
            )
            await state.clear()
            return
        
        # Check if friend exists in the system (only if not already fetched by username)
        if not friend:
            try:
                friend = await UserService.get_or_create_user(session, friend_id)
            except Exception:
                await message.answer(
                    get_text(lang, "friend_not_found"),
                    reply_markup=get_friends_menu_keyboard(lang)
                )
                await state.clear()
                return
        
        # Check if friend is approved
        if friend.status != UserStatus.APPROVED:
            await message.answer(
                get_text(lang, "friend_not_found"),
                reply_markup=get_friends_menu_keyboard(lang)
            )
            await state.clear()
            return
        
        # Send friend request
        success = await mongo_service.send_friend_request(message.from_user.id, friend_id)
        
        if success:
            # Send notification to the friend
            try:
                # Get requester's info
                requester_name = user.first_name or user.username or f"User {message.from_user.id}"
                requester_username = user.username or str(message.from_user.id)
                
                # Get friend's language
                friend_lang = friend.interface_language.value
                
                # Send notification using message.bot
                await message.bot.send_message(
                    friend_id,
                    get_text(friend_lang, "friend_request_notification",
                           name=requester_name,
                           username=requester_username)
                )
            except Exception:
                # If notification fails, that's okay - the request is still sent
                pass
            
            await message.answer(
                get_text(lang, "friend_request_sent"),
                reply_markup=get_friends_menu_keyboard(lang)
            )
        else:
            await message.answer(
                get_text(lang, "friend_request_exists"),
                reply_markup=get_friends_menu_keyboard(lang)
            )
        
        await state.clear()


@router.callback_query(F.data == "friends_remove")
async def remove_friend_prompt(callback: CallbackQuery):
    """Show list of friends to remove"""
    try:
        async with async_session_maker() as session:
            user = await UserService.get_or_create_user(session, callback.from_user.id)
            lang = user.interface_language.value
            
            # Get friends list
            friend_ids = await mongo_service.get_friends(callback.from_user.id)
            
            if not friend_ids:
                await callback.message.edit_text(
                    get_text(lang, "no_friends"),
                    reply_markup=get_friends_menu_keyboard(lang)
                )
                await callback.answer()
                return
            
            # Get friend details
            friends = []
            for friend_id in friend_ids:
                friend = await UserService.get_or_create_user(session, friend_id)
                friend_name = friend.first_name or friend.username or f"User {friend_id}"
                friends.append((friend_id, friend_name))
            
            text = get_text(lang, "friends_list", 
                           friends_list="\n".join([f"👤 {name}" for _, name in friends]))
            text += "\n\n" + ("Оберіть друга для видалення:" if lang == "uk" else "Выберите друга для удаления:")
            
            await callback.message.edit_text(
                text,
                reply_markup=get_friend_list_keyboard(lang, friends)
            )
        
        await callback.answer()
    except Exception:
        # Ensure callback is always answered to prevent button from appearing stuck
        await callback.answer()
        raise


@router.callback_query(F.data.startswith("remove_friend_"))
async def process_remove_friend(callback: CallbackQuery):
    """Process friend removal"""
    friend_id = int(callback.data.split("_")[2])
    
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, callback.from_user.id)
        lang = user.interface_language.value
        
        # Remove friend
        success = await mongo_service.remove_friend(callback.from_user.id, friend_id)
        
        if success:
            await callback.message.edit_text(
                get_text(lang, "friend_removed"),
                reply_markup=get_friends_menu_keyboard(lang)
            )
        else:
            await callback.message.edit_text(
                get_text(lang, "error"),
                reply_markup=get_friends_menu_keyboard(lang)
            )
    
    await callback.answer()


@router.callback_query(F.data == "friends_stats")
async def view_friends_stats(callback: CallbackQuery):
    """View friends' statistics"""
    try:
        async with async_session_maker() as session:
            user = await UserService.get_or_create_user(session, callback.from_user.id)
            lang = user.interface_language.value

            friend_ids = await mongo_service.get_friends(callback.from_user.id)
            if not friend_ids:
                await callback.message.edit_text(
                    get_text(lang, "no_friends"),
                    reply_markup=get_friends_menu_keyboard(lang)
                )
                await callback.answer()
                return

            stats_map = await mongo_service.get_today_stats_bulk(friend_ids)
            friends_rows = []
            for friend_id in friend_ids:
                friend = await UserService.get_or_create_user(session, friend_id)
                friend_name, friend_username = _friend_display_name(friend, friend_id)
                friend_stats = stats_map.get(friend_id, {})
                streak_info = await mongo_service.get_streak(friend_id)
                streak = streak_info.get("current", 0)
                activity_score = (
                    friend_stats.get("completed", 0)
                    + friend_stats.get("flashcard_know", 0)
                    + friend_stats.get("flashcard_retry", 0)
                )
                is_active_today = activity_score > 0
                friends_rows.append({
                    "friend_name": friend_name,
                    "friend_username": friend_username,
                    "stats": friend_stats,
                    "streak": streak,
                    "is_active_today": is_active_today,
                    "activity_score": activity_score,
                })

            friends_rows.sort(
                key=lambda item: (
                    0 if item["is_active_today"] else 1,
                    -item["activity_score"],
                    -item["stats"].get("quality", 0),
                    -item["streak"],
                    item["friend_name"].lower(),
                )
            )

            text = get_text(lang, "friends_stats_title")

            for item in friends_rows:
                text += _build_friend_stats_text(
                    lang,
                    item["friend_name"],
                    item["friend_username"],
                    item["stats"],
                    item["streak"],
                )
            
            await callback.message.edit_text(
                text,
                reply_markup=get_friends_menu_keyboard(lang)
            )
        
        await callback.answer()
    except Exception:
        # Ensure callback is always answered to prevent button from appearing stuck
        await callback.answer()
        raise


@router.callback_query(F.data == "friends_pending")
async def view_pending_requests(callback: CallbackQuery):
    """View incoming pending friend requests"""
    try:
        async with async_session_maker() as session:
            user = await UserService.get_or_create_user(session, callback.from_user.id)
            lang = user.interface_language.value
            
            # Get pending incoming requests
            requester_ids = await mongo_service.get_pending_incoming_requests(callback.from_user.id)
            
            if not requester_ids:
                await callback.message.edit_text(
                    get_text(lang, "no_pending_requests"),
                    reply_markup=get_friends_menu_keyboard(lang)
                )
                await callback.answer()
                return
            
            # Get requester details
            requesters = []
            for requester_id in requester_ids:
                requester = await UserService.get_or_create_user(session, requester_id)
                requester_name = requester.first_name or requester.username or f"User {requester_id}"
                requesters.append((requester_id, requester_name))
            
            text = get_text(lang, "pending_requests_title")
            text += "\n".join([f"👤 {name}" for _, name in requesters])
            text += "\n\n" + get_text(lang, "pending_requests_instructions")
            
            await callback.message.edit_text(
                text,
                reply_markup=get_pending_requests_keyboard(lang, requesters)
            )
        
        await callback.answer()
    except Exception:
        # Ensure callback is always answered to prevent button from appearing stuck
        await callback.answer()
        raise


@router.callback_query(F.data == "friends_outgoing")
async def view_outgoing_requests(callback: CallbackQuery):
    """View outgoing pending friend requests."""
    try:
        async with async_session_maker() as session:
            user = await UserService.get_or_create_user(session, callback.from_user.id)
            lang = user.interface_language.value

            friend_ids = await mongo_service.get_pending_outgoing_requests(callback.from_user.id)

            if not friend_ids:
                await callback.message.edit_text(
                    get_text(lang, "no_outgoing_requests"),
                    reply_markup=get_friends_menu_keyboard(lang)
                )
                await callback.answer()
                return

            lines = []
            for friend_id in friend_ids:
                friend = await UserService.get_or_create_user(session, friend_id)
                friend_name, friend_username = _friend_display_name(friend, friend_id)
                lines.append(f"👤 {friend_name} (@{friend_username})")

            text = get_text(lang, "outgoing_requests_title") + "\n".join(lines)
            await callback.message.edit_text(
                text,
                reply_markup=get_friends_menu_keyboard(lang)
            )

        await callback.answer()
    except Exception:
        await callback.answer()
        raise


@router.callback_query(F.data.startswith("accept_request_"))
async def accept_friend_request(callback: CallbackQuery):
    """Accept a friend request"""
    requester_id = int(callback.data.split("_")[2])
    
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, callback.from_user.id)
        lang = user.interface_language.value
        
        # Accept the request
        success = await mongo_service.accept_friend_request(callback.from_user.id, requester_id)
        
        if success:
            # Send notification to the requester
            try:
                # Get user's info
                user_name = user.first_name or user.username or f"User {callback.from_user.id}"
                user_username = user.username or str(callback.from_user.id)
                
                # Get requester's language
                requester = await UserService.get_or_create_user(session, requester_id)
                requester_lang = requester.interface_language.value
                
                # Send notification using callback.bot
                await callback.bot.send_message(
                    requester_id,
                    get_text(requester_lang, "friend_request_accepted_notification",
                           name=user_name,
                           username=user_username)
                )
            except Exception:
                pass
            
            await callback.message.edit_text(
                get_text(lang, "friend_request_accepted"),
                reply_markup=get_friends_menu_keyboard(lang)
            )
        else:
            await callback.message.edit_text(
                get_text(lang, "error"),
                reply_markup=get_friends_menu_keyboard(lang)
            )
    
    await callback.answer()


@router.callback_query(F.data.startswith("reject_request_"))
async def reject_friend_request(callback: CallbackQuery):
    """Reject a friend request"""
    requester_id = int(callback.data.split("_")[2])
    
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, callback.from_user.id)
        lang = user.interface_language.value
        
        # Reject the request
        success = await mongo_service.reject_friend_request(callback.from_user.id, requester_id)
        
        if success:
            await callback.message.edit_text(
                get_text(lang, "friend_request_rejected"),
                reply_markup=get_friends_menu_keyboard(lang)
            )
        else:
            await callback.message.edit_text(
                get_text(lang, "error"),
                reply_markup=get_friends_menu_keyboard(lang)
            )
    
    await callback.answer()


@router.callback_query(F.data == "friends_back")
async def friends_back_to_main(callback: CallbackQuery, state: FSMContext):
    """Return to main menu"""
    await state.clear()
    
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, callback.from_user.id)
        lang = user.interface_language.value
        
        from bot.utils.keyboards import get_main_menu_keyboard
        
        await callback.message.answer(
            get_text(lang, "main_menu"),
            reply_markup=get_main_menu_keyboard(user)
        )
        
        # Delete the inline keyboard message
        try:
            await callback.message.delete()
        except Exception:
            pass
    
    await callback.answer()
