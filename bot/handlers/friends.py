from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from bot.models.database import UserStatus, async_session_maker
from bot.services.database_service import UserService
from bot.services import mongo_service
from bot.locales.texts import get_text
from bot.utils.keyboards import get_friends_menu_keyboard, get_friend_list_keyboard


router = Router()


class FriendsStates(StatesGroup):
    """FSM states for friends management"""
    waiting_for_friend_id = State()


@router.message(F.text.in_([
    "👥 Друзья", "👥 Друзі"
]))
async def friends_menu(message: Message, state: FSMContext):
    """Show friends menu"""
    await state.clear()
    
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, message.from_user.id)
        
        if user.status != UserStatus.APPROVED:
            return
        
        # Check if trial expired
        if UserService.is_trial_expired(user):
            lang = user.interface_language.value
            from bot.config import settings
            await message.answer(
                get_text(lang, "trial_expired", 
                        payment_link=settings.STRIPE_PAYMENT_LINK,
                        admin_contact=settings.ADMIN_CONTACT)
            )
            return
        
        lang = user.interface_language.value
        
        # Get friends list
        friend_ids = await mongo_service.get_friends(message.from_user.id)
        
        if friend_ids:
            # Get friend details
            friends_list = []
            for friend_id in friend_ids:
                friend = await UserService.get_or_create_user(session, friend_id)
                friend_name = friend.first_name or friend.username or f"User {friend_id}"
                friends_list.append(f"👤 {friend_name} (@{friend.username or friend_id})")
            
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
                friend_name = friend.first_name or friend.username or f"User {friend_id}"
                friends_list.append(f"👤 {friend_name} (@{friend.username or friend_id})")
            
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
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, message.from_user.id)
        lang = user.interface_language.value
        
        # Parse friend identifier (ID or username)
        friend_identifier = message.text.strip()
        
        # Try to parse as ID first
        friend_id = None
        if friend_identifier.startswith("@"):
            # Username provided
            username = friend_identifier[1:]
            # Search for user by username - we need to add this method
            # For now, show error
            await message.answer(
                get_text(lang, "friend_not_found") + "\n\n💡 " + 
                ("Будь ласка, використовуйте Telegram ID користувача." if lang == "uk" 
                 else "Пожалуйста, используйте Telegram ID пользователя."),
                reply_markup=get_friends_menu_keyboard(lang)
            )
            await state.clear()
            return
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
        
        # Check if friend exists in the system
        try:
            friend = await UserService.get_or_create_user(session, friend_id)
            if friend.status != UserStatus.APPROVED:
                await message.answer(
                    get_text(lang, "friend_not_found"),
                    reply_markup=get_friends_menu_keyboard(lang)
                )
                await state.clear()
                return
        except Exception:
            await message.answer(
                get_text(lang, "friend_not_found"),
                reply_markup=get_friends_menu_keyboard(lang)
            )
            await state.clear()
            return
        
        # Add friend
        success = await mongo_service.add_friend(message.from_user.id, friend_id)
        
        if success:
            await message.answer(
                get_text(lang, "friend_added"),
                reply_markup=get_friends_menu_keyboard(lang)
            )
        else:
            await message.answer(
                get_text(lang, "friend_already_exists"),
                reply_markup=get_friends_menu_keyboard(lang)
            )
        
        await state.clear()


@router.callback_query(F.data == "friends_remove")
async def remove_friend_prompt(callback: CallbackQuery):
    """Show list of friends to remove"""
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
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, callback.from_user.id)
        lang = user.interface_language.value
        
        # Get friends' stats
        friends_stats = await mongo_service.get_friends_stats(callback.from_user.id)
        
        if not friends_stats:
            await callback.message.edit_text(
                get_text(lang, "friends_stats_empty"),
                reply_markup=get_friends_menu_keyboard(lang)
            )
            await callback.answer()
            return
        
        # Build stats message
        text = get_text(lang, "friends_stats_title")
        
        for friend_id, stats in friends_stats.items():
            friend = await UserService.get_or_create_user(session, friend_id)
            friend_name = friend.first_name or friend.username or f"User {friend_id}"
            friend_username = friend.username or str(friend_id)
            
            text += get_text(lang, "friends_stats_user",
                           name=friend_name,
                           username=friend_username,
                           completed=stats.get("completed", 0),
                           quality=stats.get("quality", 0))
        
        await callback.message.edit_text(
            text,
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
