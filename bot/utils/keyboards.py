from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from bot.locales.texts import get_text
from typing import Any, Optional


def get_language_selection_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for selecting interface language"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🇺🇦 Українська", callback_data="lang_uk")
    builder.button(text="Русский", callback_data="lang_ru")
    builder.adjust(2)
    return builder.as_markup()


def get_main_menu_keyboard(user: Any) -> ReplyKeyboardMarkup:
    """Main menu keyboard based on user language"""
    lang = user.interface_language.value
    builder = ReplyKeyboardBuilder()
    
    builder.button(text=get_text(lang, "btn_translator"))
    builder.button(text=get_text(lang, "btn_daily_trainer"))
    builder.button(text=get_text(lang, "btn_express_trainer"))
    builder.button(text=get_text(lang, "btn_my_progress"))
    builder.button(text=get_text(lang, "btn_flashcards"))
    builder.button(text=get_text(lang, "btn_saved_words"))
    builder.button(text=get_text(lang, "btn_friends"))
    builder.button(text=get_text(lang, "btn_settings"))
    builder.button(text=get_text(lang, "btn_support"))
    # Admins get an extra button to open admin panel
    from bot.config import settings
    if getattr(user, "telegram_id", None) in settings.admin_id_list:
        builder.button(text=get_text(lang, "btn_admin"))
    
    # Layout: 2 columns for main feature buttons (4 rows), then 1 column for support (and admin if applicable)
    builder.adjust(2, 2, 2, 2, 1, 1, 1)
    return builder.as_markup(resize_keyboard=True)


def get_admin_menu_keyboard(lang: str) -> ReplyKeyboardMarkup:
    """Admin menu keyboard"""
    builder = ReplyKeyboardBuilder()
    
    builder.button(text=get_text(lang, "btn_pending_users"))
    builder.button(text=get_text(lang, "btn_user_stats"))
    builder.button(text=get_text(lang, "btn_broadcast"))
    builder.button(text=get_text(lang, "btn_user_rating"))
     # New: manage user access (trial/30 days/unlimited)
    builder.button(text=get_text(lang, "btn_user_access"))
    builder.button(text=get_text(lang, "btn_back"))
    
    builder.adjust(2, 2, 1, 1)
    return builder.as_markup(resize_keyboard=True)


def get_settings_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Settings menu keyboard"""
    builder = InlineKeyboardBuilder()
    
    builder.button(text=get_text(lang, "interface_lang"), callback_data="settings_interface_lang")
    builder.button(text=get_text(lang, "learning_lang"), callback_data="settings_learning_lang")
    # Difficulty level removed - now handled through topic selection in trainer settings
    builder.button(text=get_text(lang, "btn_back"), callback_data="settings_back")
    
    builder.adjust(1)
    return builder.as_markup()


def get_interface_language_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for selecting interface language in settings"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🇺🇦 Українська", callback_data="set_interface_uk")
    builder.button(text="🇷🇺 Русский", callback_data="set_interface_ru")
    builder.button(text="⬅️", callback_data="settings_back")
    builder.adjust(2, 1)
    return builder.as_markup()


def get_learning_language_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Keyboard for selecting learning language"""
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text(lang, "btn_english"), callback_data="set_learning_en")
    builder.button(text=get_text(lang, "btn_german"), callback_data="set_learning_de")
    builder.button(text=get_text(lang, "btn_back"), callback_data="settings_back")
    builder.adjust(2, 1)
    return builder.as_markup()


def get_difficulty_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Keyboard for selecting difficulty level"""
    builder = InlineKeyboardBuilder()
    builder.button(text="A2", callback_data="set_difficulty_A2")
    builder.button(text="B1", callback_data="set_difficulty_B1")
    builder.button(text="B2", callback_data="set_difficulty_B2")
    builder.button(text="A2-B2", callback_data="set_difficulty_A2-B2")
    builder.button(text=get_text(lang, "btn_back"), callback_data="settings_back")
    builder.adjust(4, 1)
    return builder.as_markup()


def get_translator_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Keyboard for translator mode"""
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text(lang, "btn_save"), callback_data="save_word")
    builder.adjust(1)
    return builder.as_markup()


def get_trainer_keyboard(user: Any) -> InlineKeyboardMarkup:
    """Keyboard for daily trainer"""
    lang = user.interface_language.value
    builder = InlineKeyboardBuilder()
    
    if user.daily_trainer_enabled:
        builder.button(text=get_text(lang, "btn_stop_trainer"), callback_data="trainer_stop")
    else:
        builder.button(text=get_text(lang, "btn_start_trainer"), callback_data="trainer_start")
    
    # Настройки тренажера
    builder.button(text=get_text(lang, "btn_trainer_settings"), callback_data="trainer_settings")
    
    builder.adjust(1, 1)
    return builder.as_markup()


def get_trainer_task_keyboard(lang: str, training_id: str) -> InlineKeyboardMarkup:
    """Keyboard for training task with hint button"""
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text(lang, "btn_get_hint"), callback_data=f"hint_{training_id}")
    builder.adjust(1)
    return builder.as_markup()


def get_trainer_settings_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Keyboard for trainer settings"""
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text(lang, "btn_set_time_period"), callback_data="trainer_set_time")
    builder.button(text=get_text(lang, "btn_set_message_count"), callback_data="trainer_set_count")
    builder.button(text=get_text(lang, "btn_set_topic"), callback_data="trainer_set_topic")
    builder.button(text=get_text(lang, "btn_back"), callback_data="trainer_back")
    builder.adjust(1)
    return builder.as_markup()


def get_time_period_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Keyboard for selecting time period"""
    builder = InlineKeyboardBuilder()
    # Предустановленные периоды
    builder.button(text="🌅 06:00 - 12:00", callback_data="time_06_12")
    builder.button(text="☀️ 09:00 - 18:00", callback_data="time_09_18")
    builder.button(text="🌆  12:00 - 20:00", callback_data="time_12_20")
    builder.button(text="🌙 15:00 - 23:00", callback_data="time_15_23")
    builder.button(text=get_text(lang, "btn_back"), callback_data="trainer_settings")
    builder.adjust(2, 2, 1)
    return builder.as_markup()


def get_message_count_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Keyboard for selecting message count per day"""
    builder = InlineKeyboardBuilder()
    for i in range(1, 11):
        builder.button(text=f"{i}", callback_data=f"count_{i}")
    builder.button(text=get_text(lang, "btn_back"), callback_data="trainer_settings")
    builder.adjust(5, 5, 1)
    return builder.as_markup()


def get_user_approval_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Keyboard for approving/rejecting users and managing access"""
    builder = InlineKeyboardBuilder()
    # Basic approval actions
    builder.button(text="✅ Approve", callback_data=f"approve_{user_id}")
    builder.button(text="❌ Reject", callback_data=f"reject_{user_id}")
    # Access management actions
    builder.button(text="🧪 Trial 10d", callback_data=f"access_trial_{user_id}")
    builder.button(text="📅 30 days", callback_data=f"access_30_{user_id}")
    builder.button(text="♾ Unlimited", callback_data=f"access_unlimited_{user_id}")
    builder.adjust(2, 3)
    return builder.as_markup()


def get_user_access_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Keyboard for managing access for a specific user by ID"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🧪 Trial 10d", callback_data=f"access_trial_{user_id}")
    builder.button(text="📅 30 days", callback_data=f"access_30_{user_id}")
    builder.button(text="♾ Unlimited", callback_data=f"access_unlimited_{user_id}")
    builder.adjust(3)
    return builder.as_markup()


def get_broadcast_confirm_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for confirming broadcast"""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Yes", callback_data="broadcast_confirm_yes")
    builder.button(text="❌ No", callback_data="broadcast_confirm_no")
    builder.adjust(2)
    return builder.as_markup()


def get_topic_level_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Keyboard for selecting topic level category"""
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text(lang, "btn_topic_level_a2"), callback_data="topic_level_a2")
    builder.button(text=get_text(lang, "btn_topic_level_b1"), callback_data="topic_level_b1")
    builder.button(text=get_text(lang, "btn_topic_level_b2"), callback_data="topic_level_b2")
    builder.button(text=get_text(lang, "btn_random_topic"), callback_data="set_topic_random")
    builder.button(text=get_text(lang, "btn_back"), callback_data="trainer_settings")
    builder.adjust(3, 1, 1)
    return builder.as_markup()


def get_topic_selection_keyboard(lang: str, level: str) -> InlineKeyboardMarkup:
    """Keyboard for selecting specific topic within a level"""
    from bot.models.database import TrainerTopic, TOPIC_METADATA
    
    builder = InlineKeyboardBuilder()
    
    # Filter topics by level
    for topic in TrainerTopic:
        if topic == TrainerTopic.RANDOM:
            continue
        metadata = TOPIC_METADATA.get(topic)
        if metadata and metadata["level"] == level:
            topic_text = get_text(lang, f"topic_{topic.value}")
            builder.button(text=topic_text, callback_data=f"set_topic_{topic.value}")
    
    # Add random topic button for this level
    builder.button(text=get_text(lang, "btn_random_topic"), callback_data=f"set_topic_random_{level.lower()}")
    builder.button(text=get_text(lang, "btn_back"), callback_data="trainer_set_topic")
    builder.adjust(1)
    return builder.as_markup()


def get_friends_menu_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Keyboard for friends menu"""
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text(lang, "btn_add_friend"), callback_data="friends_add")
    builder.button(text=get_text(lang, "btn_remove_friend"), callback_data="friends_remove")
    builder.button(text=get_text(lang, "btn_pending_requests"), callback_data="friends_pending")
    builder.button(text=get_text(lang, "btn_view_friends_stats"), callback_data="friends_stats")
    builder.button(text=get_text(lang, "btn_main_menu"), callback_data="friends_back")
    builder.adjust(2, 1, 1, 1)
    return builder.as_markup()


def get_friend_list_keyboard(lang: str, friends: list) -> InlineKeyboardMarkup:
    """Keyboard with list of friends for removal"""
    builder = InlineKeyboardBuilder()
    for friend_id, friend_name in friends:
        builder.button(text=f"❌ {friend_name}", callback_data=f"remove_friend_{friend_id}")
    builder.button(text=get_text(lang, "btn_back"), callback_data="friends_menu")
    builder.adjust(1)
    return builder.as_markup()


def get_pending_requests_keyboard(lang: str, requesters: list) -> InlineKeyboardMarkup:
    """Keyboard with list of pending friend requests"""
    builder = InlineKeyboardBuilder()
    for requester_id, requester_name in requesters:
        builder.button(text=f"✅ {requester_name}", callback_data=f"accept_request_{requester_id}")
        builder.button(text=f"❌ {requester_name}", callback_data=f"reject_request_{requester_id}")
    builder.button(text=get_text(lang, "btn_back"), callback_data="friends_menu")
    builder.adjust(2)
    return builder.as_markup()


def get_cancel_keyboard(lang: str) -> ReplyKeyboardMarkup:
    """Simple keyboard with cancel button"""
    builder = ReplyKeyboardBuilder()
    builder.button(text=get_text(lang, "btn_cancel"))
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)


def get_express_trainer_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Keyboard for express trainer menu"""
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text(lang, "btn_start_express"), callback_data="express_start")
    builder.button(text=get_text(lang, "btn_express_settings"), callback_data="express_settings")
    builder.adjust(1)
    return builder.as_markup()


def get_express_task_keyboard(lang: str, training_id: str) -> InlineKeyboardMarkup:
    """Keyboard for express training task with hint and next sentence buttons"""
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text(lang, "btn_get_hint"), callback_data=f"hint_{training_id}")
    builder.adjust(1)
    return builder.as_markup()


def get_express_next_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Keyboard for getting next express training task"""
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text(lang, "btn_get_next_sentence"), callback_data="express_next")
    builder.adjust(1)
    return builder.as_markup()


def get_express_settings_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Keyboard for express trainer settings"""
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text(lang, "btn_set_topic"), callback_data="express_set_topic")
    builder.button(text=get_text(lang, "btn_back"), callback_data="express_back")
    builder.adjust(1)
    return builder.as_markup()


def get_express_topic_level_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Keyboard for selecting topic level category for express trainer"""
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text(lang, "btn_topic_level_a2"), callback_data="express_topic_level_a2")
    builder.button(text=get_text(lang, "btn_topic_level_b1"), callback_data="express_topic_level_b1")
    builder.button(text=get_text(lang, "btn_topic_level_b2"), callback_data="express_topic_level_b2")
    builder.button(text=get_text(lang, "btn_random_topic"), callback_data="express_set_topic_random")
    builder.button(text=get_text(lang, "btn_back"), callback_data="express_settings")
    builder.adjust(3, 1, 1)
    return builder.as_markup()


def get_express_topic_selection_keyboard(lang: str, level: str) -> InlineKeyboardMarkup:
    """Keyboard for selecting specific topic within a level for express trainer"""
    from bot.models.database import TrainerTopic, TOPIC_METADATA
    
    builder = InlineKeyboardBuilder()
    
    # Filter topics by level
    for topic in TrainerTopic:
        if topic == TrainerTopic.RANDOM:
            continue
        metadata = TOPIC_METADATA.get(topic)
        if metadata and metadata["level"] == level:
            topic_text = get_text(lang, f"topic_{topic.value}")
            builder.button(text=topic_text, callback_data=f"express_set_topic_{topic.value}")
    
    # Add random topic button for this level
    builder.button(text=get_text(lang, "btn_random_topic"), callback_data=f"express_set_topic_random_{level.lower()}")
    builder.button(text=get_text(lang, "btn_back"), callback_data="express_set_topic")
    builder.adjust(1)
    return builder.as_markup()


# Flashcard keyboards
def get_flashcards_menu_keyboard(lang: str, webapp_url: Optional[str] = None) -> InlineKeyboardMarkup:
    """Main flashcards menu keyboard with optional Web App button"""
    builder = InlineKeyboardBuilder()
    
    # Add Web App button if URL is configured
    if webapp_url:
        builder.button(
            text=get_text(lang, "btn_open_webapp"),
            web_app=WebAppInfo(url=f"{webapp_url}/flashcards")
        )
    
    builder.button(text=get_text(lang, "btn_my_sets"), callback_data="flashcards_my_sets")
    builder.button(text=get_text(lang, "btn_create_set"), callback_data="flashcards_create_set")
    builder.adjust(1)
    return builder.as_markup()


def get_flashcard_sets_keyboard(sets: list, lang: str) -> InlineKeyboardMarkup:
    """Keyboard showing list of flashcard sets"""
    builder = InlineKeyboardBuilder()
    cards_word = get_text(lang, "flashcards_cards_count")
    for s in sets:
        set_id = str(s["_id"])
        builder.button(text=f"📚 {s['name']} ({s.get('card_count', 0)} {cards_word})", callback_data=f"flashcards_view_set_{set_id}")
    builder.button(text=get_text(lang, "btn_back"), callback_data="flashcards_menu")
    builder.adjust(1)
    return builder.as_markup()


def get_flashcard_set_keyboard(set_id: str, lang: str, has_cards: bool = True) -> InlineKeyboardMarkup:
    """Keyboard for managing a flashcard set"""
    builder = InlineKeyboardBuilder()
    if has_cards:
        builder.button(text=get_text(lang, "btn_view_cards"), callback_data=f"flashcards_study_{set_id}")
    builder.button(text=get_text(lang, "btn_add_card"), callback_data=f"flashcards_add_card_{set_id}")
    builder.button(text=get_text(lang, "btn_delete_set"), callback_data=f"flashcards_delete_set_{set_id}")
    builder.button(text=get_text(lang, "btn_back"), callback_data="flashcards_my_sets")
    builder.adjust(1)
    return builder.as_markup()


def get_flashcard_view_keyboard(set_id: str, card_id: str, current: int, total: int, is_flipped: bool, lang: str) -> InlineKeyboardMarkup:
    """Keyboard for viewing and navigating flashcards"""
    builder = InlineKeyboardBuilder()
    
    # Flip button
    flip_text = get_text(lang, "btn_flip_card")
    builder.button(text=flip_text, callback_data=f"flashcards_flip_{set_id}_{card_id}_{1 if is_flipped else 0}")
    
    # Navigation buttons
    nav_buttons = []
    if current > 1:
        nav_buttons.append(InlineKeyboardButton(text=get_text(lang, "btn_prev_card"), callback_data=f"flashcards_nav_{set_id}_{current - 1}"))
    if current < total:
        nav_buttons.append(InlineKeyboardButton(text=get_text(lang, "btn_next_card"), callback_data=f"flashcards_nav_{set_id}_{current + 1}"))
    
    if nav_buttons:
        builder.row(*nav_buttons)
    
    # Delete and back buttons
    builder.button(text=get_text(lang, "btn_delete_card"), callback_data=f"flashcards_delete_card_{set_id}_{card_id}")
    builder.button(text=get_text(lang, "btn_back"), callback_data=f"flashcards_view_set_{set_id}")
    
    builder.adjust(1, len(nav_buttons) if nav_buttons else 1, 1, 1)
    return builder.as_markup()


def get_delete_set_confirm_keyboard(set_id: str, lang: str) -> InlineKeyboardMarkup:
    """Confirmation keyboard for deleting a flashcard set"""
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text(lang, "btn_confirm_delete"), callback_data=f"flashcards_confirm_delete_{set_id}")
    builder.button(text=get_text(lang, "btn_back"), callback_data=f"flashcards_view_set_{set_id}")
    builder.adjust(1)
    return builder.as_markup()

