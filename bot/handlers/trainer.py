from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from bot.models.database import UserStatus, DifficultyLevel, TrainerTopic, TOPIC_METADATA, LearningLanguage, async_session_maker
from bot.services.database_service import UserService, TrainingService
from bot.services.translation_service import translation_service
from bot.locales.texts import get_text
from bot.utils.keyboards import get_trainer_keyboard, get_main_menu_keyboard
from bot.config import settings
from bot.services import mongo_service
from bot.handlers.admin import is_admin


router = Router()


class TrainerStates(StatesGroup):
    waiting_for_answer = State()


@router.message(F.text.in_([
    "🎯 Ежедневный тренажёр", "🎯 Щоденний тренажер"
]))
async def trainer_menu(message: Message, state: FSMContext):
    """Show daily trainer menu"""
    # Clear any previous state (like translator mode)
    await state.clear()
    
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, message.from_user.id)
        
        if user.status != UserStatus.APPROVED:
            return
        
        lang = user.interface_language.value
        
        # Trainer is free for all approved users - no subscription check needed
        
        # Show current trainer status
        if user.daily_trainer_enabled:
            # Get progress and countdown information
            from bot.services.scheduler_service import scheduler_service
            tasks_sent, total_tasks = await scheduler_service.get_daily_progress(user)
            _, countdown = await scheduler_service.calculate_next_task_time(user)
            
            # Build status message with progress and countdown
            base_text = get_text(lang, "trainer_started")
            status_text = get_text(lang, "trainer_status", 
                                  completed=tasks_sent, 
                                  total=total_tasks, 
                                  countdown=countdown)
            text = f"{base_text}\n\n{status_text}"
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
        
        # Get progress and countdown information
        from bot.services.scheduler_service import scheduler_service
        tasks_sent, total_tasks = await scheduler_service.get_daily_progress(user)
        _, countdown = await scheduler_service.calculate_next_task_time(user)
        
        # Build status message with progress and countdown
        base_text = get_text(lang, "trainer_started")
        status_text = get_text(lang, "trainer_status", 
                              completed=tasks_sent, 
                              total=total_tasks, 
                              countdown=countdown)
        text = f"{base_text}\n\n{status_text}"
        
        await callback.message.edit_text(
            text,
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
        
        # Get topic name for display using metadata and learning language
        topic = user.trainer_topic or TrainerTopic.RANDOM
        if topic == TrainerTopic.RANDOM:
            topic_text = get_text(lang, "btn_random_topic")
        else:
            metadata = TOPIC_METADATA.get(topic)
            if metadata:
                # Choose label based on learning language (German/English)
                if user.learning_language == LearningLanguage.GERMAN:
                    topic_text = metadata.get("de") or get_text(lang, f"topic_{topic.value}")
                else:
                    topic_text = metadata.get("en") or get_text(lang, f"topic_{topic.value}")
            else:
                topic_text = get_text(lang, f"topic_{topic.value}")
        
        text = get_text(lang, "trainer_settings_menu",
                       start=user.trainer_start_time or "09:00",
                       end=user.trainer_end_time or "21:00",
                       count=user.trainer_messages_per_day or 3,
                       topic=topic_text)
        
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
            # Get progress and countdown information
            from bot.services.scheduler_service import scheduler_service
            tasks_sent, total_tasks = await scheduler_service.get_daily_progress(user)
            _, countdown = await scheduler_service.calculate_next_task_time(user)
            
            # Build status message with progress and countdown
            base_text = get_text(lang, "trainer_started")
            status_text = get_text(lang, "trainer_status", 
                                  completed=tasks_sent, 
                                  total=total_tasks, 
                                  countdown=countdown)
            text = f"{base_text}\n\n{status_text}"
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
    from bot.services.scheduler_service import scheduler_service
    
    # Parse time from callback data: time_09_18 -> 09:00, 18:00
    parts = callback.data.split("_")
    start_hour = parts[1]
    end_hour = parts[2]
    start_time = f"{start_hour}:00"
    end_time = f"{end_hour}:00"
    
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, callback.from_user.id)
        lang = user.interface_language.value
        
        # Update user settings (this updates both the object in memory and the database)
        await UserService.update_user(session, user, 
                                      trainer_start_time=start_time,
                                      trainer_end_time=end_time)
        
        # When time window changes, reset today's counters so scheduling
        # starts fresh with the new settings
        from bot.services.redis_service import redis_service
        from datetime import datetime
        from zoneinfo import ZoneInfo
        now_kyiv = datetime.now(ZoneInfo('Europe/Kyiv'))
        current_date = now_kyiv.date()
        tasks_today_key = f"tasks_today:{user.id}:{current_date}"
        last_task_time_key = f"last_task_time:{user.id}:{current_date}"
        await redis_service.delete(tasks_today_key)
        await redis_service.delete(last_task_time_key)
        
        # Get updated progress using the already-updated user object
        if user.daily_trainer_enabled:
            tasks_sent, total_tasks = await scheduler_service.get_daily_progress(user)
            _, countdown = await scheduler_service.calculate_next_task_time(user)
            progress_info = "\n\n" + get_text(lang, "trainer_status", 
                                              completed=tasks_sent, 
                                              total=total_tasks, 
                                              countdown=countdown)
        else:
            progress_info = ""
        
        await callback.message.edit_text(
            get_text(lang, "time_period_updated", start=start_time, end=end_time) + progress_info,
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
    from bot.services.scheduler_service import scheduler_service
    
    # Parse count from callback data: count_5 -> 5
    count = int(callback.data.split("_")[1])
    
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, callback.from_user.id)
        lang = user.interface_language.value
        
        # Update user settings (this updates both the object in memory and the database)
        await UserService.update_user(session, user, trainer_messages_per_day=count)
        
        # When daily count changes, reset today's counters so scheduling
        # adapts cleanly to the new limit
        from bot.services.redis_service import redis_service
        from datetime import datetime
        from zoneinfo import ZoneInfo
        now_kyiv = datetime.now(ZoneInfo('Europe/Kyiv'))
        current_date = now_kyiv.date()
        tasks_today_key = f"tasks_today:{user.id}:{current_date}"
        last_task_time_key = f"last_task_time:{user.id}:{current_date}"
        await redis_service.delete(tasks_today_key)
        await redis_service.delete(last_task_time_key)
        
        # Get updated progress using the already-updated user object
        if user.daily_trainer_enabled:
            tasks_sent, total_tasks = await scheduler_service.get_daily_progress(user)
            _, countdown = await scheduler_service.calculate_next_task_time(user)
            progress_info = "\n\n" + get_text(lang, "trainer_status", 
                                              completed=tasks_sent, 
                                              total=total_tasks, 
                                              countdown=countdown)
        else:
            progress_info = ""
        
        await callback.message.edit_text(
            get_text(lang, "message_count_updated", count=count) + progress_info,
            reply_markup=get_trainer_settings_keyboard(lang)
        )
    
    await callback.answer()


@router.callback_query(F.data == "trainer_set_topic")
async def show_topic_selection(callback: CallbackQuery):
    """Show topic level selection"""
    from bot.utils.keyboards import get_topic_level_keyboard
    
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, callback.from_user.id)
        lang = user.interface_language.value
        
        await callback.message.edit_text(
            get_text(lang, "select_topic"),
            reply_markup=get_topic_level_keyboard(lang)
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("topic_level_"))
async def show_topic_list(callback: CallbackQuery):
    """Show topics for selected level"""
    from bot.utils.keyboards import get_topic_selection_keyboard
    
    # Parse level from callback data: topic_level_a2 -> a2
    level = callback.data.split("_")[2].upper()
    
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, callback.from_user.id)
        lang = user.interface_language.value
        
        await callback.message.edit_text(
            get_text(lang, "select_topic"),
            reply_markup=get_topic_selection_keyboard(lang, level)
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("set_topic_"))
async def set_topic(callback: CallbackQuery):
    """Set trainer topic"""
    from bot.utils.keyboards import get_trainer_settings_keyboard
    from bot.services.redis_service import redis_service
    
    # Parse topic from callback data: set_topic_personal_info -> personal_info
    topic_value = callback.data.replace("set_topic_", "")
    
    # Check if it's a level-specific random topic (e.g., random_a2, random_b1, random_b2)
    if topic_value.startswith("random_") and topic_value != "random":
        # Level-specific random: store the level in Redis
        level = topic_value.replace("random_", "").upper()  # e.g., "a2" -> "A2"
        
        async with async_session_maker() as session:
            user = await UserService.get_or_create_user(session, callback.from_user.id)
            lang = user.interface_language.value
            
            # Set topic to random in user settings (this updates both the object in memory and the database)
            await UserService.update_user(session, user, trainer_topic=TrainerTopic.RANDOM)
            
            # Store the specific level in Redis for random selection
            await redis_service.set(f"random_topic_level:{user.id}", level, ex=None)
            
            # Get updated progress using the already-updated user object
            from bot.services.scheduler_service import scheduler_service
            if user.daily_trainer_enabled:
                tasks_sent, total_tasks = await scheduler_service.get_daily_progress(user)
                _, countdown = await scheduler_service.calculate_next_task_time(user)
                progress_info = "\n\n" + get_text(lang, "trainer_status", 
                                                  completed=tasks_sent, 
                                                  total=total_tasks, 
                                                  countdown=countdown)
            else:
                progress_info = ""
            
            await callback.message.edit_text(
                get_text(lang, "topic_updated") + progress_info,
                reply_markup=get_trainer_settings_keyboard(lang)
            )
        
        await callback.answer()
        return
    
    try:
        topic = TrainerTopic(topic_value)
    except ValueError:
        # Invalid topic, ignore
        await callback.answer()
        return
    
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, callback.from_user.id)
        lang = user.interface_language.value
        
        # Update user settings (this updates both the object in memory and the database)
        await UserService.update_user(session, user, trainer_topic=topic)
        
        # Clear any level-specific random setting
        await redis_service.delete(f"random_topic_level:{user.id}")
        
        # Get updated progress using the already-updated user object
        from bot.services.scheduler_service import scheduler_service
        if user.daily_trainer_enabled:
            tasks_sent, total_tasks = await scheduler_service.get_daily_progress(user)
            _, countdown = await scheduler_service.calculate_next_task_time(user)
            progress_info = "\n\n" + get_text(lang, "trainer_status", 
                                              completed=tasks_sent, 
                                              total=total_tasks, 
                                              countdown=countdown)
        else:
            progress_info = ""
        
        await callback.message.edit_text(
            get_text(lang, "topic_updated") + progress_info,
            reply_markup=get_trainer_settings_keyboard(lang)
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("hint_"))
async def show_hint(callback: CallbackQuery):
    """Show translation hint when user requests it"""
    from bot.services.redis_service import redis_service
    from bson import ObjectId
    
    # Extract training ID from callback data: hint_<training_id>
    training_id_str = callback.data.replace("hint_", "")
    
    try:
        training_id = ObjectId(training_id_str)
    except Exception:
        await callback.answer("❌ Помилка/Ошибка")
        return
    
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, callback.from_user.id)
        lang = user.interface_language.value
        
        # Get training session from Mongo
        from bot.services import mongo_service
        training_col = mongo_service.db().training_sessions
        training = await training_col.find_one({"_id": training_id})
        
        if not training:
            await callback.answer("❌ Помилка/Ошибка")
            return
        
        # Show the hint with the expected translation
        expected_translation = training.get("expected_translation", "")
        # Remove the inline keyboard from the original message to prevent multiple clicks
        await callback.message.edit_reply_markup(reply_markup=None)
        # Send hint as a new message so the original task remains visible
        await callback.message.answer(
            get_text(lang, "hint_activated", translation=expected_translation)
        )
        
        # Track hint activation in daily stats
        from bot.services import mongo_service
        await mongo_service.track_hint_activation(user.id)
        
        # Clear training state - this task won't count towards daily stats
        await redis_service.clear_user_state(callback.from_user.id)
    
    await callback.answer()


async def send_training_task(bot, user_id: int):
    """Send a training task to user (called by scheduler)"""
    from bot.services.redis_service import redis_service
    import random
    
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, user_id)
        
        if not user.daily_trainer_enabled or user.status != UserStatus.APPROVED:
            return
        
        lang = user.interface_language.value
        learning_lang = user.learning_language.value
        difficulty = user.difficulty_level or DifficultyLevel.A2
        topic = user.trainer_topic or TrainerTopic.RANDOM
        
        # Check if there's a level-specific random topic setting
        if topic == TrainerTopic.RANDOM:
            random_level = await redis_service.get(f"random_topic_level:{user.id}")
            if random_level:
                # Level-specific random: pick a random topic from this level
                from bot.models.database import TOPIC_METADATA
                level_topics = [t for t, meta in TOPIC_METADATA.items() 
                               if meta["level"] == random_level and t != TrainerTopic.RANDOM]
                if level_topics:
                    topic = random.choice(level_topics)
            else:
                # Global random: pick random level first, then random topic from that level
                from bot.models.database import TOPIC_METADATA
                levels = ["A2", "B1", "B2"]
                random_level = random.choice(levels)
                level_topics = [t for t, meta in TOPIC_METADATA.items() 
                               if meta["level"] == random_level and t != TrainerTopic.RANDOM]
                if level_topics:
                    topic = random.choice(level_topics)
        
        # Get current progress
        from bot.services.scheduler_service import scheduler_service
        tasks_sent, total_tasks = await scheduler_service.get_daily_progress(user)
        # Hard cap: never show progress above daily limit
        if tasks_sent > total_tasks:
            tasks_sent = total_tasks
        
        # Generate sentence
        sentence = await translation_service.generate_sentence(
            difficulty.value,
            learning_lang,
            lang,
            topic
        )
        
        # Get expected translation
        expected_translation, _ = await translation_service.translate(
            sentence,
            lang,
            learning_lang,
            None  # Don't count tokens for system-generated tasks
        )
        
        # Get topic metadata for display
        from bot.models.database import TOPIC_METADATA
        topic_metadata = TOPIC_METADATA.get(topic, {"level": difficulty.value, "number": 0})
        topic_level = topic_metadata["level"]

        # Choose topic name based on learning language:
        # - if user learns German (de) -> German topic label
        # - if user learns English (en) -> English topic label
        if topic in TOPIC_METADATA:
            if user.learning_language.value == "de":
                topic_name = topic_metadata.get("de")
            elif user.learning_language.value == "en":
                topic_name = topic_metadata.get("en")
            else:
                # Fallback to German label if something unexpected
                topic_name = topic_metadata.get("de")
        else:
            # Fallback to legacy locale-based key if metadata missing
            topic_name = get_text(lang, f"topic_{topic.value}")
        
        # Create training session
        training = await TrainingService.create_session(
            session,
            user.id,
            sentence,
            expected_translation,
            difficulty,
            topic  # Pass topic to training session
        )
        # Optional mirror to Mongo
        if settings.mongo_enabled and mongo_service.is_ready():
            try:
                await mongo_service.store_training_session(user.id, sentence, expected_translation, difficulty.value)
            except Exception:
                pass
        
        # Send task to user with progress information and topic/level
        from bot.utils.keyboards import get_trainer_task_keyboard
        await bot.send_message(
            user_id,
            get_text(lang, "trainer_task_with_progress", 
                    current=tasks_sent, 
                    total=total_tasks,
                    level=topic_level,
                    topic=topic_name,
                    sentence=sentence),
            reply_markup=get_trainer_task_keyboard(lang, str(training["_id"]))
        )
        
        # Update task counter and last task time in Redis after successful send
        from datetime import datetime
        from zoneinfo import ZoneInfo
        now_kyiv = datetime.now(ZoneInfo('Europe/Kyiv'))
        current_date = now_kyiv.date()
        current_time_str = now_kyiv.time().strftime("%H:%M")
        
        tasks_today_key = f"tasks_today:{user.id}:{current_date}"
        last_task_time_key = f"last_task_time:{user.id}:{current_date}"
        
        # Increase counter by one but never above daily limit
        new_tasks_sent = min(tasks_sent + 1, total_tasks)
        await redis_service.set(tasks_today_key, new_tasks_sent, ex=86400)
        await redis_service.set(last_task_time_key, current_time_str, ex=86400)
        
        # Store training session ID in Redis for answer processing
        # Convert ObjectId to string for JSON serialization
        await redis_service.set_user_state(
            user_id,
            "awaiting_training_answer",
            {"training_id": str(training["_id"])}
        )


@router.message(F.text)
async def check_training_answer(message: Message, state: FSMContext):
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
    
    training_id_str = state.get("data", {}).get("training_id")
    if not training_id_str:
        return
    
    # Convert string back to ObjectId
    from bson import ObjectId
    try:
        training_id = ObjectId(training_id_str)
    except Exception:
        await redis_service.clear_user_state(message.from_user.id)
        return
    
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, message.from_user.id)
        lang = user.interface_language.value
        learning_lang = user.learning_language.value
        
        # Get training session
        # Fetch training session from Mongo
        training_col = mongo_service.db().training_sessions
        training = await training_col.find_one({"_id": training_id})
        if not training:
            await redis_service.clear_user_state(message.from_user.id)
            return
        
        user_answer = message.text
        
        # Send typing indicator to show the bot is processing
        await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
        
        # Check translation with quality assessment
        is_correct, correct_translation, explanation, quality_percentage = await translation_service.check_translation(
            training["sentence"],
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
        
        # Update daily stats with penalties context
        expected_tasks = user.trainer_messages_per_day or 3
        await TrainingService.update_daily_stats(
            session,
            user.id,
            quality_percentage,
            expected_tasks,
            is_correct,
        )
        
        # Update user stats
        user.total_answers += 1
        if is_correct:
            user.correct_answers += 1
        await UserService.update_user(session, user, total_answers=user.total_answers, correct_answers=user.correct_answers)
        
        # Increment activity
        await UserService.increment_activity(session, user, 2 if is_correct else 1)
        
        # Send feedback with quality percentage
        if is_correct:
            feedback = get_text(lang, "correct_answer_with_quality", quality=quality_percentage)
            await message.answer(feedback)
        else:
            await message.answer(
                get_text(
                    lang,
                    "incorrect_answer",
                    explanation=explanation or "",
                    quality=quality_percentage,
                    correct=correct_translation or ""
                )
            )
        
        # Clear training state
        await redis_service.clear_user_state(message.from_user.id)
        
        # Restore translator state if it was saved
        saved_state_key = f"saved_translator_state:{message.from_user.id}"
        saved_state = await redis_service.get(saved_state_key)
        if saved_state and saved_state != "{}":
            try:
                # Import here to avoid circular dependency
                from bot.handlers.translator import TranslatorStates
                import json
                
                # Restore the translator state using the FSM context passed to this handler
                saved_data = json.loads(saved_state)
                await state.set_state(TranslatorStates.waiting_for_text)
                await state.update_data(**saved_data)
                
                # Clear the saved state
                await redis_service.set(saved_state_key, "{}", ex=1)
            except Exception:
                # If restoration fails, user can re-enter translator mode manually
                pass
