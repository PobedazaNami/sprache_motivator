from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from bot.locales.texts import get_text
from typing import Any


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
    builder.button(text=get_text(lang, "btn_saved_words"))
    builder.button(text=get_text(lang, "btn_settings"))
    builder.button(text=get_text(lang, "btn_support"))
    
    builder.adjust(2, 2, 1)
    return builder.as_markup(resize_keyboard=True)


def get_admin_menu_keyboard(lang: str) -> ReplyKeyboardMarkup:
    """Admin menu keyboard"""
    builder = ReplyKeyboardBuilder()
    
    builder.button(text=get_text(lang, "btn_pending_users"))
    builder.button(text=get_text(lang, "btn_user_stats"))
    builder.button(text=get_text(lang, "btn_broadcast"))
    builder.button(text=get_text(lang, "btn_user_rating"))
    builder.button(text=get_text(lang, "btn_back"))
    
    builder.adjust(2, 2, 1)
    return builder.as_markup(resize_keyboard=True)


def get_settings_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Settings menu keyboard"""
    builder = InlineKeyboardBuilder()
    
    builder.button(text=get_text(lang, "interface_lang"), callback_data="settings_interface_lang")
    builder.button(text=get_text(lang, "learning_lang"), callback_data="settings_learning_lang")
    builder.button(text=get_text(lang, "difficulty"), callback_data="settings_difficulty")
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


def get_learning_language_keyboard_for_trainer(lang: str) -> InlineKeyboardMarkup:
    """Keyboard for selecting learning language from trainer settings"""
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text(lang, "btn_english"), callback_data="trainer_update_learning_en")
    builder.button(text=get_text(lang, "btn_german"), callback_data="trainer_update_learning_de")
    builder.button(text=get_text(lang, "btn_back"), callback_data="trainer_settings")
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


def get_difficulty_keyboard_for_trainer(lang: str) -> InlineKeyboardMarkup:
    """Keyboard for selecting difficulty level from trainer settings"""
    builder = InlineKeyboardBuilder()
    builder.button(text="A2", callback_data="trainer_update_difficulty_A2")
    builder.button(text="B1", callback_data="trainer_update_difficulty_B1")
    builder.button(text="B2", callback_data="trainer_update_difficulty_B2")
    builder.button(text="A2-B2", callback_data="trainer_update_difficulty_A2-B2")
    builder.button(text=get_text(lang, "btn_back"), callback_data="trainer_settings")
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


def get_training_task_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Keyboard shown with an active training task"""
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text(lang, "btn_show_translation"), callback_data="trainer_reveal_translation")
    builder.adjust(1)
    return builder.as_markup()


def get_trainer_settings_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Keyboard for trainer settings"""
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text(lang, "btn_set_time_period"), callback_data="trainer_set_time")
    builder.button(text=get_text(lang, "btn_set_message_count"), callback_data="trainer_set_count")
    builder.button(text=get_text(lang, "learning_lang"), callback_data="trainer_set_learning_lang")
    builder.button(text=get_text(lang, "difficulty"), callback_data="trainer_set_difficulty")
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
    """Keyboard for approving/rejecting users"""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Approve", callback_data=f"approve_{user_id}")
    builder.button(text="❌ Reject", callback_data=f"reject_{user_id}")
    builder.adjust(2)
    return builder.as_markup()


def get_broadcast_confirm_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for confirming broadcast"""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Yes", callback_data="broadcast_confirm_yes")
    builder.button(text="❌ No", callback_data="broadcast_confirm_no")
    builder.adjust(2)
    return builder.as_markup()
