from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from bot.models.database import UserStatus, async_session_maker
from bot.services.database_service import UserService, WordService, TranslationHistoryService
from bot.services.translation_service import translation_service
from bot.locales.texts import get_text
from bot.utils.keyboards import get_translator_keyboard, get_main_menu_keyboard
from bot.handlers.admin import is_admin


router = Router()


class TranslatorStates(StatesGroup):
    waiting_for_text = State()
    show_translation = State()


@router.message(F.text.in_([
    "📖 Переводчик", "📖 Перекладач", 
    "📖 Переводчик (подписка)", "📖 Перекладач (підписка)"
]))
async def translator_mode(message: Message, state: FSMContext):
    """Activate translator mode"""
    # Clear any previous state (FSM and Redis)
    await state.clear()
    from bot.services.redis_service import redis_service
    await redis_service.clear_user_state(message.from_user.id)
    
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, message.from_user.id)
        
        if user.status != UserStatus.APPROVED:
            return
        
        lang = user.interface_language.value
        
        # Admins have unrestricted access
        if not is_admin(message.from_user.id):
            # Check subscription status (translator requires subscription)
            if not user.subscription_active:
                from bot.config import settings
                payment_link = settings.STRIPE_PAYMENT_LINK or "Contact admin for payment"
                admin_contact = settings.ADMIN_CONTACT
                await message.answer(
                    get_text(lang, "translator_subscription_required", 
                            payment_link=payment_link,
                            admin_contact=admin_contact)
                )
                return
        
        await message.answer(get_text(lang, "translator_mode"))
        await state.set_state(TranslatorStates.waiting_for_text)
        await state.update_data(user_id=user.id, lang=lang, learning_lang=user.learning_language.value)


@router.message(
    TranslatorStates.waiting_for_text,
    ~F.text.in_([
        "📖 Переводчик", "📖 Перекладач",
        "🎯 Ежедневный тренажёр", "🎯 Щоденний тренажер",
        "⚙️ Настройки", "⚙️ Налаштування",
        "📊 Статистика", "📊 Статистика",
        "💾 Сохранённые слова", "💾 Збережені слова",
        "🔙 Главное меню", "🔙 Головне меню",
        "⚡️ Експрес тренажер", "⚡️ Экспресс тренажёр",
        "👥 Друзья", "👥 Друзі",
        "📊 Мой прогресс", "📊 Мій прогрес",
        "💬 Техподдержка", "💬 Техпідтримка"
    ])
)
async def process_translation(message: Message, state: FSMContext):
    """Process translation request"""
    # Check if user has an active training session (daily OR express)
    from bot.services.redis_service import redis_service
    import time
    
    training_state = await redis_service.get_user_state(message.from_user.id)
    if training_state:
        state_type = training_state.get("state")
        # Check if it's any type of training state
        if state_type in ["awaiting_training_answer", "awaiting_express_answer"]:
            # Check if training state is recent (within 10 minutes)
            state_timestamp = training_state.get("timestamp", 0)
            current_time = time.time()
            state_age_minutes = (current_time - state_timestamp) / 60
            
            if state_age_minutes < 10:
                # User has active RECENT training session - call appropriate trainer handler
                # Save current translator state to Redis for restoration after training
                import json
                current_data = await state.get_data()
                await redis_service.set(
                    f"saved_translator_state:{message.from_user.id}",
                    json.dumps(current_data),
                    ex=3600  # 1 hour expiry
                )
                
                # Route to appropriate handler based on state type
                if state_type == "awaiting_training_answer":
                    from bot.handlers.trainer import check_training_answer
                    await check_training_answer(message, state)
                else:  # awaiting_express_answer
                    from bot.handlers.express_trainer import check_express_answer
                    await check_express_answer(message, state)
                return
            else:
                # Training state is stale (>10 min) - clear it and proceed with translation
                await redis_service.clear_user_state(message.from_user.id)
    
    data = await state.get_data()
    lang = data.get("lang", "ru")
    learning_lang = data.get("learning_lang", "en")
    user_id = data.get("user_id")
    
    text = message.text

    # If user explicitly sends saved-words command text while in translator state,
    # route it to the saved-words handler instead of treating as text to translate.
    if text in ["💾 Сохранённые слова", "💾 Збережені слова"]:
        # Import lazily to avoid circular imports
        from bot.handlers.translator import show_saved_words
        return await show_saved_words(message)
    
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, message.from_user.id)
        
        # Admins have unrestricted access
        if not is_admin(message.from_user.id):
            # Check subscription status (translator requires subscription)
            if not user.subscription_active:
                from bot.config import settings
                payment_link = settings.STRIPE_PAYMENT_LINK or "Contact admin for payment"
                admin_contact = settings.ADMIN_CONTACT
                await message.answer(
                    get_text(lang, "translator_subscription_required", 
                            payment_link=payment_link,
                            admin_contact=admin_contact)
                )
                await state.clear()
                return
        
        try:
            # Detect source and target languages
            # Simple heuristic: if text contains Cyrillic, translate to learning language
            # Otherwise, translate to interface language
            is_cyrillic = any('\u0400' <= c <= '\u04FF' for c in text)
            
            if is_cyrillic:
                # Cyrillic text (Ukrainian/Russian): translate to learning language
                source_lang = lang
                target_lang = learning_lang
            else:
                # Non-Cyrillic text (English/German): translate to interface language
                # Use 'auto' as source to let OpenAI detect between EN/DE
                source_lang = 'auto'
                target_lang = lang
            
            # Send typing indicator to show the bot is processing
            await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
            
            # Translate
            translation, tokens = await translation_service.translate(
                text, source_lang, target_lang, user_id
            )
            
            # Save to history
            await TranslationHistoryService.save_translation(
                session, user.id, text, translation, source_lang, target_lang
            )
            
            # Increment activity and translation count
            await UserService.increment_activity(session, user, 1)
            user.translations_count += 1
            
            # Show translation
            result_text = f"{get_text(lang, 'translation_result')}\n\n{translation}"
            await message.answer(
                result_text,
                reply_markup=get_translator_keyboard(lang)
            )
            
            # Store for saving and keep in waiting_for_text state for next translation
            await state.update_data(
                last_original=text,
                last_translation=translation,
                last_source=source_lang,
                last_target=target_lang
            )
            # Stay in waiting_for_text state so user can continue translating
            await state.set_state(TranslatorStates.waiting_for_text)
            
        except Exception as e:
            if "Daily token limit" in str(e):
                await message.answer(get_text(lang, "token_limit"))
            else:
                await message.answer(get_text(lang, "translation_error"))


@router.callback_query(F.data == "save_word", TranslatorStates.waiting_for_text)
async def save_word(callback: CallbackQuery, state: FSMContext):
    """Save word to user's collection"""
    data = await state.get_data()
    lang = data.get("lang", "ru")
    
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, callback.from_user.id)
        
        await WordService.save_word(
            session,
            user.id,
            data.get("last_original"),
            data.get("last_translation"),
            data.get("last_source"),
            data.get("last_target")
        )
        
        await callback.answer(get_text(lang, "word_saved"), show_alert=True)
        
        # Increment activity
        await UserService.increment_activity(session, user, 1)
    
    # Already in waiting_for_text state, no need to change


@router.message(F.text.in_([
    "💾 Сохранённые слова", "💾 Збережені слова"
]))
async def show_saved_words(message: Message):
    """Show user's saved words"""
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, message.from_user.id)
        
        if user.status != UserStatus.APPROVED:
            return
        
        lang = user.interface_language.value
        
        words, total = await WordService.get_user_words(session, user.id, 0, 20)
        
        if not words:
            await message.answer(get_text(lang, "no_saved_words"))
            return
        
        text = get_text(lang, "saved_words_list") + "\n\n"
        for i, word in enumerate(words, 1):
            text += f"{i}. {word.original_text} → {word.translated_text}\n"
        
        if total > 20:
            text += f"\n{get_text(lang, 'saved_words_page', page=1, total=(total + 19) // 20)}"
        
        await message.answer(text)
