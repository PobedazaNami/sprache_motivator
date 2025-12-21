from aiogram import Router, F
from aiogram.filters import Filter
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from bot.models.database import UserStatus, DifficultyLevel, TrainerTopic, TOPIC_METADATA, LearningLanguage, async_session_maker
from bot.services.database_service import UserService, TrainingService
from bot.services.translation_service import translation_service
from bot.locales.texts import get_text
from bot.utils.keyboards import (
    get_express_trainer_keyboard, 
    get_express_task_keyboard,
    get_express_next_keyboard,
    get_express_settings_keyboard,
    get_express_topic_level_keyboard,
    get_express_topic_selection_keyboard
)
from bot.config import settings
from bot.services import mongo_service
from bot.services.redis_service import redis_service
import random
from bson import ObjectId
from bson.errors import InvalidId


router = Router()


class _RedisStateFilter(Filter):
    def __init__(self, expected_state: str) -> None:
        self.expected_state = expected_state

    async def __call__(self, message: Message) -> bool:
        redis_state = await redis_service.get_user_state(message.from_user.id)
        return bool(redis_state and redis_state.get("state") == self.expected_state)


class ExpressTrainerStates(StatesGroup):
    waiting_for_answer = State()


@router.message(F.text.in_([
    "⚡️ Експрес тренажер", "⚡️ Экспресс тренажёр"
]))
async def express_trainer_menu(message: Message, state: FSMContext):
    """Show express trainer menu"""
    # Clear any previous state (FSM and Redis training states)
    await state.clear()
    await redis_service.clear_user_state(message.from_user.id)
    
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, message.from_user.id)
        
        if user.status != UserStatus.APPROVED:
            return
        
        lang = user.interface_language.value
        
        # Express trainer is free for all approved users - no subscription check needed
        text = get_text(lang, "express_trainer_menu")
        
        await message.answer(text, reply_markup=get_express_trainer_keyboard(lang))


@router.callback_query(F.data == "express_start")
async def start_express_task(callback: CallbackQuery):
    """Start express trainer and send first task"""
    await send_express_task(callback.from_user.id, callback.message.bot, callback.message.chat.id)
    await callback.answer()


@router.callback_query(F.data == "express_next")
async def next_express_task(callback: CallbackQuery):
    """Send next express training task"""
    await send_express_task(callback.from_user.id, callback.message.bot, callback.message.chat.id)
    await callback.answer()


@router.callback_query(F.data == "express_settings")
async def show_express_settings(callback: CallbackQuery):
    """Show express trainer settings menu"""
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, callback.from_user.id)
        lang = user.interface_language.value
        
        # Get topic name for display using metadata and learning language
        topic = user.express_trainer_topic or TrainerTopic.RANDOM
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
        
        text = get_text(lang, "express_settings_menu", topic=topic_text)
        
        await callback.message.edit_text(
            text,
            reply_markup=get_express_settings_keyboard(lang)
        )
    
    await callback.answer()


@router.callback_query(F.data == "express_back")
async def back_to_express_menu(callback: CallbackQuery):
    """Return to express trainer main menu"""
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, callback.from_user.id)
        lang = user.interface_language.value
        
        text = get_text(lang, "express_trainer_menu")
        
        await callback.message.edit_text(text, reply_markup=get_express_trainer_keyboard(lang))
    
    await callback.answer()


@router.callback_query(F.data == "express_set_topic")
async def show_express_topic_selection(callback: CallbackQuery):
    """Show topic level selection for express trainer"""
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, callback.from_user.id)
        lang = user.interface_language.value
        
        await callback.message.edit_text(
            get_text(lang, "select_topic"),
            reply_markup=get_express_topic_level_keyboard(lang)
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("express_topic_level_"))
async def show_express_topic_list(callback: CallbackQuery):
    """Show topics for selected level in express trainer"""
    # Parse level from callback data: express_topic_level_a2 -> a2
    level = callback.data.split("_")[3].upper()
    
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, callback.from_user.id)
        lang = user.interface_language.value
        
        await callback.message.edit_text(
            get_text(lang, "select_topic"),
            reply_markup=get_express_topic_selection_keyboard(lang, level)
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("express_set_topic_"))
async def set_express_topic(callback: CallbackQuery):
    """Set express trainer topic"""
    # Parse topic from callback data: express_set_topic_personal_info -> personal_info
    # Use proper string slicing instead of replace to avoid unintended matches
    prefix = "express_set_topic_"
    if not callback.data.startswith(prefix):
        await callback.answer()
        return
    
    topic_value = callback.data[len(prefix):]
    
    # Check if it's a level-specific random topic (e.g., random_a2, random_b1, random_b2)
    if topic_value.startswith("random_") and topic_value != "random":
        # Level-specific random: store the level in Redis
        level = topic_value.replace("random_", "").upper()  # e.g., "a2" -> "A2"
        
        async with async_session_maker() as session:
            user = await UserService.get_or_create_user(session, callback.from_user.id)
            lang = user.interface_language.value
            
            # Set topic to random in user settings
            await UserService.update_user(session, user, express_trainer_topic=TrainerTopic.RANDOM)
            
            # Store the specific level in Redis with 30-day expiration to prevent indefinite memory usage
            await redis_service.set(f"express_random_topic_level:{user.id}", level, ex=2592000)  # 30 days
            
            await callback.message.edit_text(
                get_text(lang, "topic_updated"),
                reply_markup=get_express_settings_keyboard(lang)
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
        
        # Update user settings
        await UserService.update_user(session, user, express_trainer_topic=topic)
        
        # Clear any level-specific random setting
        await redis_service.delete(f"express_random_topic_level:{user.id}")
        
        await callback.message.edit_text(
            get_text(lang, "topic_updated"),
            reply_markup=get_express_settings_keyboard(lang)
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("hint_"))
async def show_hint(callback: CallbackQuery):
    """Show translation hint when user requests it"""
    # Extract training ID from callback data: hint_<training_id>
    training_id_str = callback.data.replace("hint_", "")
    
    try:
        training_id = ObjectId(training_id_str)
    except (InvalidId, ValueError):
        await callback.answer("❌ Помилка/Ошибка")
        return
    
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, callback.from_user.id)
        lang = user.interface_language.value
        
        # Get training session from Mongo
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
        # Include button to get next sentence
        await callback.message.answer(
            get_text(lang, "hint_activated", translation=expected_translation),
            reply_markup=get_express_next_keyboard(lang)
        )
        
        # Track hint activation in daily stats
        # await mongo_service.track_hint_activation(user.id)  # TODO: implement this function
        
        # Clear training state - this task won't count towards daily stats
        await redis_service.clear_user_state(callback.from_user.id)
    
    await callback.answer()


async def send_express_task(user_id: int, bot, chat_id: int):
    """Send an express training task to user"""
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, user_id)
        
        if user.status != UserStatus.APPROVED:
            return
        
        lang = user.interface_language.value
        learning_lang = user.learning_language.value
        difficulty = user.difficulty_level or DifficultyLevel.A2
        topic = user.express_trainer_topic or TrainerTopic.RANDOM
        
        # Check if there's a level-specific random topic setting
        if topic == TrainerTopic.RANDOM:
            random_level = await redis_service.get(f"express_random_topic_level:{user.id}")
            if random_level:
                # Level-specific random: pick a random topic from this level
                level_topics = [t for t, meta in TOPIC_METADATA.items() 
                               if meta["level"] == random_level and t != TrainerTopic.RANDOM]
                if level_topics:
                    topic = random.choice(level_topics)
            else:
                # Global random: pick random level first, then random topic from that level
                levels = ["A2", "B1", "B2"]
                random_level = random.choice(levels)
                level_topics = [t for t, meta in TOPIC_METADATA.items() 
                               if meta["level"] == random_level and t != TrainerTopic.RANDOM]
                if level_topics:
                    topic = random.choice(level_topics)
        
        # Generate sentence (passing user_id to avoid mastered sentences)
        sentence = await translation_service.generate_sentence(
            difficulty.value,
            learning_lang,
            lang,
            topic,
            user_id=user.id
        )
        
        # Get expected translation
        expected_translation, _ = await translation_service.translate(
            sentence,
            lang,
            learning_lang,
            None  # Don't count tokens for system-generated tasks
        )
        
        # Get topic metadata for display
        topic_metadata = TOPIC_METADATA.get(topic, {"level": difficulty.value, "number": 0})
        topic_level = topic_metadata["level"]

        # Choose topic name based on learning language
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
        
        # Send task to user with topic/level
        await bot.send_message(
            chat_id,
            get_text(lang, "express_trainer_task", 
                    level=topic_level,
                    topic=topic_name,
                    sentence=sentence),
            reply_markup=get_express_task_keyboard(lang, str(training["_id"]))
        )
        
        # Store training session ID in Redis for answer processing
        await redis_service.set_user_state(
            user_id,
            "awaiting_express_answer",
            {"training_id": str(training["_id"])}
        )


@router.message(_RedisStateFilter("awaiting_express_answer"), F.text)
async def check_express_answer(message: Message, state: FSMContext):
    """
    Check if message is an answer to express training task.
    
    This handler is registered to process messages when the user 
    has an active express training session.
    """
    # Redis state is guaranteed by _RedisStateFilter
    redis_state = await redis_service.get_user_state(message.from_user.id)
    
    training_id_str = redis_state.get("data", {}).get("training_id")
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
        
        # Get training session from Mongo
        training_col = mongo_service.db().training_sessions
        training = await training_col.find_one({"_id": training_id})
        if not training:
            await redis_service.clear_user_state(message.from_user.id)
            return
        
        user_answer = message.text
        
        # Send typing indicator to show the bot is processing
        await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
        
        # Check translation with quality assessment
        try:
            is_correct, correct_translation, explanation, quality_percentage = await translation_service.check_translation(
                training["sentence"],
                user_answer,
                learning_lang,
                lang
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Error checking translation: {e}")
            await message.answer(get_text(lang, "translation_error"))
            await redis_service.clear_user_state(message.from_user.id)
            return
        
        # Update training session with quality
        await TrainingService.update_session(
            session,
            training_id,
            user_answer,
            is_correct,
            explanation,
            quality_percentage
        )
        
        # Update user stats
        user.total_answers += 1
        if is_correct:
            user.correct_answers += 1
        await UserService.update_user(session, user, total_answers=user.total_answers, correct_answers=user.correct_answers)
        
        # Increment activity
        await UserService.increment_activity(session, user, 2 if is_correct else 1)
        
        # If 100% quality, mark sentence as mastered (won't be shown again)
        if quality_percentage == 100:
            topic_value = training.get("topic") if training.get("topic") else None
            await mongo_service.add_mastered_sentence(
                user_id=user.id,
                sentence=training["sentence"],
                translation=correct_translation or training.get("expected_translation", ""),
                topic=topic_value,
                difficulty=training.get("difficulty_level")
            )
        
        # Update streak (motivation system)
        streak_days, is_milestone, milestone = await mongo_service.update_streak(user.id)
        
        # Build feedback message with streak info
        feedback_parts = []
        
        if is_correct:
            feedback_parts.append(get_text(lang, "correct_answer_with_quality", quality=quality_percentage))
        else:
            feedback_parts.append(get_text(
                lang,
                "incorrect_answer",
                explanation=explanation or "",
                quality=quality_percentage,
                correct=correct_translation or ""
            ))
        
        # Add streak message if active
        if streak_days > 1:
            feedback_parts.append(get_text(lang, "streak_message", days=streak_days))
        
        # Add milestone celebration
        if is_milestone and milestone:
            milestone_key = f"streak_milestone_{milestone}"
            feedback_parts.append(get_text(lang, milestone_key))
        
        # Add perfect day message if 100%
        if quality_percentage == 100:
            feedback_parts.append(get_text(lang, "perfect_day"))
        
        # Add encouragement after mistake
        if not is_correct and quality_percentage < 70:
            feedback_parts.append(get_text(lang, "encouragement_after_mistake"))
        
        await message.answer("\n\n".join(feedback_parts), reply_markup=get_express_next_keyboard(lang))
        
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
