from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from bot.models.database import UserStatus, DifficultyLevel, async_session_maker
from bot.services.database_service import UserService, TrainingService
from bot.services.translation_service import translation_service
from bot.locales.texts import get_text
from bot.utils.keyboards import get_trainer_keyboard, get_main_menu_keyboard
from bot.config import settings
from bot.services import mongo_service


router = Router()


class TrainerStates(StatesGroup):
    waiting_for_answer = State()


@router.message(F.text.in_([
    "🎯 Ежедневный тренажёр", "🎯 Щоденний тренажер"
]))
async def trainer_menu(message: Message):
    """Show daily trainer menu"""
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, message.from_user.id)
        
        if user.status != UserStatus.APPROVED:
            return
        
        lang = user.interface_language.value
        
        # Show current trainer status
        if user.daily_trainer_enabled:
            text = get_text(lang, "trainer_started")
        else:
            text = get_text(lang, "trainer_menu")
        
        await message.answer(text, reply_markup=get_trainer_keyboard(user))


@router.callback_query(F.data == "trainer_start")
async def start_trainer(callback: CallbackQuery):
    """Start daily trainer"""
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, callback.from_user.id)
        
        lang = user.interface_language.value
        
        # Enable trainer
        await UserService.update_user(session, user, daily_trainer_enabled=True)
        # Refresh user to get updated state
        await session.refresh(user)
        
        await callback.message.edit_text(
            get_text(lang, "trainer_started"),
            reply_markup=get_trainer_keyboard(user)
        )
    
    await callback.answer()


@router.callback_query(F.data == "trainer_stop")
async def stop_trainer(callback: CallbackQuery):
    """Stop daily trainer"""
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, callback.from_user.id)
        
        lang = user.interface_language.value
        
        # Disable trainer
        await UserService.update_user(session, user, daily_trainer_enabled=False)
        # Refresh user to get updated state
        await session.refresh(user)
        
        await callback.message.edit_text(
            get_text(lang, "trainer_stopped"),
            reply_markup=get_trainer_keyboard(user)
        )
    
    await callback.answer()


@router.callback_query(F.data == "trainer_settings")
async def show_trainer_settings(callback: CallbackQuery):
    """Show trainer settings menu"""
    from bot.utils.keyboards import get_trainer_settings_keyboard
    
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, callback.from_user.id)
        lang = user.interface_language.value
        
        text = get_text(lang, "trainer_settings_menu",
                       start=user.trainer_start_time or "09:00",
                       end=user.trainer_end_time or "21:00",
                       count=user.trainer_messages_per_day or 3)
        
        await callback.message.edit_text(
            text,
            reply_markup=get_trainer_settings_keyboard(lang)
        )
    
    await callback.answer()


@router.callback_query(F.data == "trainer_back")
async def back_to_trainer_menu(callback: CallbackQuery):
    """Return to trainer main menu"""
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, callback.from_user.id)
        lang = user.interface_language.value
        
        if user.daily_trainer_enabled:
            text = get_text(lang, "trainer_started")
        else:
            text = get_text(lang, "trainer_menu")
        
        await callback.message.edit_text(text, reply_markup=get_trainer_keyboard(user))
    
    await callback.answer()


@router.callback_query(F.data == "trainer_set_time")
async def show_time_selection(callback: CallbackQuery):
    """Show time period selection"""
    from bot.utils.keyboards import get_time_period_keyboard
    
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, callback.from_user.id)
        lang = user.interface_language.value
        
        await callback.message.edit_text(
            get_text(lang, "select_time_period"),
            reply_markup=get_time_period_keyboard(lang)
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("time_"))
async def set_time_period(callback: CallbackQuery):
    """Set training time period"""
    from bot.utils.keyboards import get_trainer_settings_keyboard
    
    # Parse time from callback data: time_09_18 -> 09:00, 18:00
    parts = callback.data.split("_")
    start_hour = parts[1]
    end_hour = parts[2]
    start_time = f"{start_hour}:00"
    end_time = f"{end_hour}:00"
    
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, callback.from_user.id)
        lang = user.interface_language.value
        
        # Update user settings
        await UserService.update_user(session, user, 
                                      trainer_start_time=start_time,
                                      trainer_end_time=end_time)
        
        await callback.message.edit_text(
            get_text(lang, "time_period_updated", start=start_time, end=end_time),
            reply_markup=get_trainer_settings_keyboard(lang)
        )
    
    await callback.answer()


@router.callback_query(F.data == "trainer_set_count")
async def show_count_selection(callback: CallbackQuery):
    """Show message count selection"""
    from bot.utils.keyboards import get_message_count_keyboard
    
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, callback.from_user.id)
        lang = user.interface_language.value
        
        await callback.message.edit_text(
            get_text(lang, "select_message_count"),
            reply_markup=get_message_count_keyboard(lang)
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("count_"))
async def set_message_count(callback: CallbackQuery):
    """Set daily message count"""
    from bot.utils.keyboards import get_trainer_settings_keyboard
    
    # Parse count from callback data: count_5 -> 5
    count = int(callback.data.split("_")[1])
    
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, callback.from_user.id)
        lang = user.interface_language.value
        
        # Update user settings
        await UserService.update_user(session, user, trainer_messages_per_day=count)
        
        await callback.message.edit_text(
            get_text(lang, "message_count_updated", count=count),
            reply_markup=get_trainer_settings_keyboard(lang)
        )
    
    await callback.answer()


async def send_training_task(bot, user_id: int):
    """Send a training task to user (called by scheduler)"""
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, user_id)
        
        if not user.daily_trainer_enabled or user.status != UserStatus.APPROVED:
            return
        
        lang = user.interface_language.value
        learning_lang = user.learning_language.value
        difficulty = user.difficulty_level or DifficultyLevel.A2
        
        # Generate sentence
        sentence = await translation_service.generate_sentence(
            difficulty.value,
            learning_lang,
            lang
        )
        
        # Get expected translation
        expected_translation, _ = await translation_service.translate(
            sentence,
            lang,
            learning_lang,
            None  # Don't count tokens for system-generated tasks
        )
        
        # Create training session
        training = await TrainingService.create_session(
            session,
            user.id,
            sentence,
            expected_translation,
            difficulty
        )
        # Optional mirror to Mongo
        if settings.mongo_enabled and mongo_service.is_ready():
            try:
                await mongo_service.store_training_session(user.id, sentence, expected_translation, difficulty.value)
            except Exception:
                pass
        
        # Send task to user
        await bot.send_message(
            user_id,
            get_text(lang, "trainer_task", sentence=sentence)
        )
        
        # Store training session ID in Redis for answer processing
        from bot.services.redis_service import redis_service
        await redis_service.set_user_state(
            user_id,
            "awaiting_training_answer",
            {"training_id": training.id}
        )


@router.message(F.text)
async def check_training_answer(message: Message):
    """
    Check if message is an answer to training task.
    
    This handler is registered last and will only process messages
    when the user has an active training session. It returns early
    if no training state is found, minimizing overhead for regular messages.
    """
    from bot.services.redis_service import redis_service
    
    # Early return if not in training mode - minimal overhead
    state = await redis_service.get_user_state(message.from_user.id)
    if not state or state.get("state") != "awaiting_training_answer":
        return
    
    training_id = state.get("data", {}).get("training_id")
    if not training_id:
        return
    
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, message.from_user.id)
        lang = user.interface_language.value
        learning_lang = user.learning_language.value
        
        # Get training session
        from sqlalchemy import select
        from bot.models.database import TrainingSession
        
        result = await session.execute(
            select(TrainingSession).where(TrainingSession.id == training_id)
        )
        training = result.scalar_one_or_none()
        
        if not training:
            await redis_service.clear_user_state(message.from_user.id)
            return
        
        user_answer = message.text
        
        # Check translation with quality assessment
        is_correct, correct_translation, explanation, quality_percentage = await translation_service.check_translation(
            training.sentence,
            user_answer,
            learning_lang,
            lang
        )
        
        # Update training session with quality
        await TrainingService.update_session(
            session,
            training_id,
            user_answer,
            is_correct,
            explanation,
            quality_percentage
        )
        
        # Update daily stats
        await TrainingService.update_daily_stats(
            session,
            user.id,
            quality_percentage
        )
        
        # Update user stats
        user.total_answers += 1
        if is_correct:
            user.correct_answers += 1
        await session.commit()
        
        # Increment activity
        await UserService.increment_activity(session, user, 2 if is_correct else 1)
        
        # Send feedback with quality percentage
        if is_correct:
            feedback = get_text(lang, "correct_answer_with_quality", quality=quality_percentage)
            await message.answer(feedback)
        else:
            await message.answer(
                get_text(lang, "incorrect_answer",
                        correct=correct_translation,
                        explanation=explanation or "",
                        quality=quality_percentage)
            )
        
        # Clear state
        await redis_service.clear_user_state(message.from_user.id)
