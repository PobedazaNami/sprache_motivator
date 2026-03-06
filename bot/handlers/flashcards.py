from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timezone, timedelta
import random
from bson import ObjectId

from bot.config import settings
from bot.models.database import UserStatus, async_session_maker
from bot.services.database_service import UserService
from bot.services import mongo_service
from bot.locales.texts import get_text
from bot.utils.keyboards import (
    get_flashcards_menu_keyboard,
    get_flashcard_sets_keyboard,
    get_flashcard_set_keyboard,
    get_flashcard_view_keyboard,
    get_delete_set_confirm_keyboard,
    get_fc_session_front_keyboard,
    get_fc_session_back_keyboard,
)

router = Router()


class FlashcardStates(StatesGroup):
    creating_set = State()
    adding_card_front = State()
    adding_card_back = State()
    adding_card_example = State()


class FlashcardSessionStates(StatesGroup):
    in_session = State()


def get_default_srs_status(card: dict) -> str:
    """Return a normalized SRS status for cards created before SRS fields existed."""
    return card.get("srs_status") or "new"


def is_due_card(card: dict, now: datetime) -> bool:
    """Return True when a card should be shown in the global study session."""
    status = get_default_srs_status(card)
    if status == "new":
        return True

    next_review = card.get("srs_next_review")
    if next_review is None:
        return True

    return next_review <= now


async def get_flashcards_stats(user_id: int) -> dict:
    """Aggregate flashcard statistics for the dashboard."""
    now = datetime.now(timezone.utc)
    collection = mongo_service.db().flashcards

    new_count = await collection.count_documents(
        {
            "user_id": user_id,
            "$or": [
                {"srs_status": {"$exists": False}},
                {"srs_status": "new"},
            ],
        }
    )
    learning_count = await collection.count_documents({"user_id": user_id, "srs_status": "learning"})
    known_count = await collection.count_documents({"user_id": user_id, "srs_status": "known"})
    due_count = await collection.count_documents(
        {
            "user_id": user_id,
            "$or": [
                {"srs_status": {"$exists": False}},
                {"srs_status": "new"},
                {"srs_next_review": {"$exists": False}},
                {"srs_next_review": {"$lte": now}},
            ],
        }
    )

    return {
        "new": new_count,
        "learning": learning_count,
        "known": known_count,
        "due": due_count,
    }


async def get_flashcards_dashboard_text(lang: str, user_id: int) -> str:
    """Build dashboard text for the flashcards home screen."""
    stats = await get_flashcards_stats(user_id)
    return get_text(
        lang,
        "fc_stats_header",
        new=stats["new"],
        learning=stats["learning"],
        known=stats["known"],
        due=stats["due"],
    )


async def get_due_cards(user_id: int, limit: int = 50) -> list[dict]:
    """Return due cards from all sets, shuffled for a study session."""
    now = datetime.now(timezone.utc)
    cards = await mongo_service.db().flashcards.find({"user_id": user_id}).to_list(length=5000)
    due_cards = [card for card in cards if is_due_card(card, now)]
    random.shuffle(due_cards)
    return due_cards[:limit]


def get_next_interval(current_interval: int) -> int:
    """Advance the card interval using a simple DuoCards-like schedule."""
    if current_interval <= 0:
        return 1
    if current_interval == 1:
        return 3
    if current_interval == 3:
        return 7
    if current_interval == 7:
        return 14
    if current_interval == 14:
        return 30
    return current_interval * 2


def build_srs_update(card: dict, known: bool) -> dict:
    """Build a MongoDB update document for a self-rated flashcard answer."""
    now = datetime.now(timezone.utc)
    current_interval = int(card.get("srs_interval", 0) or 0)

    if known:
        next_interval = get_next_interval(current_interval)
        status = "known" if next_interval >= 7 else "learning"
        return {
            "$set": {
                "srs_status": status,
                "srs_interval": next_interval,
                "srs_next_review": now + timedelta(days=next_interval),
            },
            "$inc": {"srs_correct": 1},
        }

    return {
        "$set": {
            "srs_status": "learning",
            "srs_interval": 1,
            "srs_next_review": now + timedelta(days=1),
        },
        "$inc": {"srs_incorrect": 1},
    }


async def show_session_card(message, card: dict, current: int, total: int, is_flipped: bool, lang: str):
    """Render a flashcard inside the global SRS session."""
    if is_flipped:
        text = get_text(lang, "fc_session_card_back", current=current, total=total, front=card["front"], back=card["back"])
        keyboard = get_fc_session_back_keyboard(lang)
    else:
        text = get_text(lang, "fc_session_card_front", current=current, total=total, front=card["front"])
        keyboard = get_fc_session_front_keyboard(lang)

    try:
        await message.edit_text(text, reply_markup=keyboard)
    except Exception:
        await message.answer(text, reply_markup=keyboard)


async def show_session_current_card(message, state: FSMContext, lang: str):
    """Load and show the current card from session state."""
    data = await state.get_data()
    queue = data.get("session_queue", [])
    index = data.get("session_index", 0)

    if index >= len(queue):
        summary = get_text(
            lang,
            "fc_session_complete",
            correct=data.get("session_correct", 0),
            incorrect=data.get("session_incorrect", 0),
            total=len(queue),
        )
        await state.clear()
        await message.edit_text(summary, reply_markup=get_flashcards_menu_keyboard(lang, settings.WEBAPP_URL))
        return

    card = await mongo_service.db().flashcards.find_one({"_id": ObjectId(queue[index])})
    if not card:
        await state.update_data(session_index=index + 1)
        await show_session_current_card(message, state, lang)
        return

    await show_session_card(message, card, index + 1, len(queue), False, lang)


async def advance_session(message, state: FSMContext, lang: str):
    """Move session to the next card and render it."""
    data = await state.get_data()
    await state.update_data(session_index=data.get("session_index", 0) + 1)
    await show_session_current_card(message, state, lang)


@router.message(F.text.in_([
    "🎴 Картки", "🎴 Карточки"
]))
async def flashcards_menu(message: Message, state: FSMContext):
    """Show flashcards main menu"""
    await state.clear()
    
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, message.from_user.id)
        
        if user.status != UserStatus.APPROVED:
            return
        
        lang = user.interface_language.value
        text = await get_flashcards_dashboard_text(lang, message.from_user.id)
        
        # Check if Mini App is configured
        webapp_url = settings.WEBAPP_URL
        await message.answer(text, reply_markup=get_flashcards_menu_keyboard(lang, webapp_url))


@router.callback_query(F.data == "flashcards_menu")
async def flashcards_menu_callback(callback: CallbackQuery, state: FSMContext):
    """Show flashcards main menu from callback"""
    await state.clear()
    
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, callback.from_user.id)
        lang = user.interface_language.value
        text = await get_flashcards_dashboard_text(lang, callback.from_user.id)
        
        # Check if Mini App is configured
        webapp_url = settings.WEBAPP_URL
        await callback.message.edit_text(text, reply_markup=get_flashcards_menu_keyboard(lang, webapp_url))
        await callback.answer()


@router.callback_query(F.data == "fc_session_start")
async def start_flashcards_session(callback: CallbackQuery, state: FSMContext):
    """Start a global flashcard review session across all decks."""
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, callback.from_user.id)
        lang = user.interface_language.value

        if not mongo_service.is_ready():
            await callback.answer(get_text(lang, "error"), show_alert=True)
            return

        due_cards = await get_due_cards(callback.from_user.id)
        if not due_cards:
            await state.clear()
            await callback.message.edit_text(
                get_text(lang, "fc_session_empty"),
                reply_markup=get_flashcards_menu_keyboard(lang, settings.WEBAPP_URL),
            )
            await callback.answer()
            return

        await state.set_state(FlashcardSessionStates.in_session)
        await state.update_data(
            session_queue=[str(card["_id"]) for card in due_cards],
            session_index=0,
            session_correct=0,
            session_incorrect=0,
        )
        await show_session_card(callback.message, due_cards[0], 1, len(due_cards), False, lang)
        await callback.answer()


@router.callback_query(F.data == "fc_session_flip")
async def flip_session_card(callback: CallbackQuery, state: FSMContext):
    """Flip the current card inside an SRS session."""
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, callback.from_user.id)
        lang = user.interface_language.value

        data = await state.get_data()
        queue = data.get("session_queue", [])
        index = data.get("session_index", 0)

        if index >= len(queue):
            await callback.answer(get_text(lang, "error"), show_alert=True)
            return

        card = await mongo_service.db().flashcards.find_one({"_id": ObjectId(queue[index])})
        if not card:
            await advance_session(callback.message, state, lang)
            await callback.answer()
            return

        await show_session_card(callback.message, card, index + 1, len(queue), True, lang)
        await callback.answer()


@router.callback_query(F.data == "fc_session_know")
async def mark_session_card_known(callback: CallbackQuery, state: FSMContext):
    """Mark the current session card as known and schedule the next review."""
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, callback.from_user.id)
        lang = user.interface_language.value

        data = await state.get_data()
        queue = data.get("session_queue", [])
        index = data.get("session_index", 0)

        if index >= len(queue):
            await callback.answer(get_text(lang, "error"), show_alert=True)
            return

        card = await mongo_service.db().flashcards.find_one({"_id": ObjectId(queue[index])})
        if card:
            await mongo_service.db().flashcards.update_one(
                {"_id": card["_id"], "user_id": callback.from_user.id},
                build_srs_update(card, known=True),
            )

        await state.update_data(session_correct=data.get("session_correct", 0) + 1)
        await advance_session(callback.message, state, lang)
        await callback.answer()


@router.callback_query(F.data == "fc_session_dontknow")
async def mark_session_card_unknown(callback: CallbackQuery, state: FSMContext):
    """Mark the current session card as unknown and reset it for near-term review."""
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, callback.from_user.id)
        lang = user.interface_language.value

        data = await state.get_data()
        queue = data.get("session_queue", [])
        index = data.get("session_index", 0)

        if index >= len(queue):
            await callback.answer(get_text(lang, "error"), show_alert=True)
            return

        card = await mongo_service.db().flashcards.find_one({"_id": ObjectId(queue[index])})
        if card:
            await mongo_service.db().flashcards.update_one(
                {"_id": card["_id"], "user_id": callback.from_user.id},
                build_srs_update(card, known=False),
            )

        await state.update_data(session_incorrect=data.get("session_incorrect", 0) + 1)
        await advance_session(callback.message, state, lang)
        await callback.answer()


@router.callback_query(F.data == "fc_session_skip")
async def skip_session_card(callback: CallbackQuery, state: FSMContext):
    """Skip the current session card without updating its SRS state."""
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, callback.from_user.id)
        lang = user.interface_language.value

        await advance_session(callback.message, state, lang)
        await callback.answer()


@router.callback_query(F.data == "fc_session_exit")
async def exit_flashcards_session(callback: CallbackQuery, state: FSMContext):
    """Exit the current flashcard session and show the partial results."""
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, callback.from_user.id)
        lang = user.interface_language.value

        data = await state.get_data()
        queue = data.get("session_queue", [])
        summary = get_text(
            lang,
            "fc_session_exit",
            correct=data.get("session_correct", 0),
            incorrect=data.get("session_incorrect", 0),
            total=min(data.get("session_index", 0), len(queue)),
        )
        await state.clear()
        await callback.message.edit_text(summary, reply_markup=get_flashcards_menu_keyboard(lang, settings.WEBAPP_URL))
        await callback.answer()


@router.callback_query(F.data == "flashcards_my_sets")
async def show_my_sets(callback: CallbackQuery):
    """Show user's flashcard sets"""
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, callback.from_user.id)
        lang = user.interface_language.value
        
        if not mongo_service.is_ready():
            await callback.answer(get_text(lang, "error"), show_alert=True)
            return
        
        # Get user's flashcard sets
        sets = await mongo_service.db().flashcard_sets.find(
            {"user_id": callback.from_user.id}
        ).sort("created_at", -1).to_list(length=100)
        
        # Add card count to each set
        for s in sets:
            card_count = await mongo_service.db().flashcards.count_documents(
                {"set_id": str(s["_id"])}
            )
            s["card_count"] = card_count
        
        if not sets:
            text = get_text(lang, "flashcards_no_sets")
            await callback.message.edit_text(text, reply_markup=get_flashcards_menu_keyboard(lang))
        else:
            text = get_text(lang, "flashcards_my_sets", sets="")
            await callback.message.edit_text(text, reply_markup=get_flashcard_sets_keyboard(sets, lang))
        
        await callback.answer()


@router.callback_query(F.data == "flashcards_create_set")
async def create_set_start(callback: CallbackQuery, state: FSMContext):
    """Start creating a new flashcard set"""
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, callback.from_user.id)
        lang = user.interface_language.value
        
        text = get_text(lang, "flashcards_create_set")
        await callback.message.answer(text)
        await state.set_state(FlashcardStates.creating_set)
        await callback.answer()


@router.message(FlashcardStates.creating_set)
async def create_set_finish(message: Message, state: FSMContext):
    """Finish creating a flashcard set"""
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, message.from_user.id)
        lang = user.interface_language.value
        
        if not mongo_service.is_ready():
            await message.answer(get_text(lang, "error"))
            await state.clear()
            return
        
        set_name = message.text.strip()
        
        # Create the set
        set_doc = {
            "user_id": message.from_user.id,
            "name": set_name,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        
        result = await mongo_service.db().flashcard_sets.insert_one(set_doc)
        
        await state.clear()
        text = get_text(lang, "flashcards_set_created", name=set_name)
        await message.answer(text, reply_markup=get_flashcards_menu_keyboard(lang))


@router.callback_query(F.data.startswith("flashcards_view_set_"))
async def view_set(callback: CallbackQuery):
    """View a specific flashcard set"""
    set_id = callback.data.split("_")[-1]
    
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, callback.from_user.id)
        lang = user.interface_language.value
        
        if not mongo_service.is_ready():
            await callback.answer(get_text(lang, "error"), show_alert=True)
            return
        
        try:
            flashcard_set = await mongo_service.db().flashcard_sets.find_one(
                {"_id": ObjectId(set_id), "user_id": callback.from_user.id}
            )
            
            if not flashcard_set:
                await callback.answer(get_text(lang, "error"), show_alert=True)
                return
            
            # Count cards in the set
            card_count = await mongo_service.db().flashcards.count_documents(
                {"set_id": set_id}
            )
            
            created_date = flashcard_set["created_at"].strftime("%d.%m.%Y")
            text = get_text(
                lang, 
                "flashcards_set_info",
                name=flashcard_set["name"],
                count=card_count,
                created=created_date,
                description=""
            )
            
            await callback.message.edit_text(
                text, 
                reply_markup=get_flashcard_set_keyboard(set_id, lang, has_cards=(card_count > 0))
            )
            await callback.answer()
            
        except Exception as e:
            await callback.answer(get_text(lang, "error"), show_alert=True)


@router.callback_query(F.data.startswith("flashcards_add_card_"))
async def add_card_start(callback: CallbackQuery, state: FSMContext):
    """Start adding a card to a set"""
    set_id = callback.data.split("_")[-1]
    
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, callback.from_user.id)
        lang = user.interface_language.value
        
        if not mongo_service.is_ready():
            await callback.answer(get_text(lang, "error"), show_alert=True)
            return
        
        try:
            flashcard_set = await mongo_service.db().flashcard_sets.find_one(
                {"_id": ObjectId(set_id), "user_id": callback.from_user.id}
            )
            
            if not flashcard_set:
                await callback.answer(get_text(lang, "error"), show_alert=True)
                return
            
            await state.update_data(set_id=set_id, set_name=flashcard_set["name"])
            await state.set_state(FlashcardStates.adding_card_front)
            
            text = get_text(lang, "flashcards_add_card", set_name=flashcard_set["name"])
            await callback.message.answer(text)
            await callback.answer()
            
        except Exception as e:
            await callback.answer(get_text(lang, "error"), show_alert=True)


@router.message(FlashcardStates.adding_card_front)
async def add_card_front(message: Message, state: FSMContext):
    """Save front side and ask for back side"""
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, message.from_user.id)
        lang = user.interface_language.value
        
        await state.update_data(front_text=message.text.strip())
        await state.set_state(FlashcardStates.adding_card_back)
        
        text = get_text(lang, "flashcards_enter_back")
        await message.answer(text)


@router.message(FlashcardStates.adding_card_back)
async def add_card_back(message: Message, state: FSMContext):
    """Save back side and ask for example sentence"""
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, message.from_user.id)
        lang = user.interface_language.value
        
        if not mongo_service.is_ready():
            await message.answer(get_text(lang, "error"))
            await state.clear()
            return
        
        data = await state.get_data()
        set_id = data.get("set_id")
        front_text = data.get("front_text")
        back_text = message.text.strip()

        await state.update_data(back_text=back_text)
        await state.set_state(FlashcardStates.adding_card_example)

        text = get_text(lang, "flashcards_enter_example")
        await message.answer(text)


@router.message(FlashcardStates.adding_card_example)
async def add_card_example(message: Message, state: FSMContext):
    """Save the complete card including example sentence"""
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, message.from_user.id)
        lang = user.interface_language.value

        if not mongo_service.is_ready():
            await message.answer(get_text(lang, "error"))
            await state.clear()
            return

        data = await state.get_data()
        set_id = data.get("set_id")
        front_text = data.get("front_text")
        back_text = data.get("back_text")
        example_text = message.text.strip()

        # Create the card
        card_doc = {
            "user_id": message.from_user.id,
            "set_id": set_id,
            "front": front_text,
            "back": back_text,
            "example": example_text,
            "created_at": datetime.now(timezone.utc)
        }

        await mongo_service.db().flashcards.insert_one(card_doc)

        # Update set's updated_at
        await mongo_service.db().flashcard_sets.update_one(
            {"_id": ObjectId(set_id)},
            {"$set": {"updated_at": datetime.now(timezone.utc)}}
        )

        await state.clear()
        text = get_text(lang, "flashcards_card_created")
        await message.answer(text, reply_markup=get_flashcards_menu_keyboard(lang))


@router.callback_query(F.data.startswith("flashcards_study_"))
async def study_cards(callback: CallbackQuery, state: FSMContext):
    """Start studying cards in a set"""
    set_id = callback.data.split("_")[-1]
    
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, callback.from_user.id)
        lang = user.interface_language.value
        
        if not mongo_service.is_ready():
            await callback.answer(get_text(lang, "error"), show_alert=True)
            return
        
        # Get all cards in the set
        cards = await mongo_service.db().flashcards.find(
            {"set_id": set_id}
        ).sort("created_at", 1).to_list(length=1000)
        
        if not cards:
            await callback.answer(get_text(lang, "flashcards_no_cards"), show_alert=True)
            return
        
        # Show first card
        await show_card(callback.message, set_id, cards[0], 1, len(cards), False, lang)
        await callback.answer()


async def show_card(message, set_id: str, card: dict, current: int, total: int, is_flipped: bool, lang: str):
    """Display a flashcard"""
    card_id = str(card["_id"])
    
    if is_flipped:
        side_text = get_text(lang, "flashcards_card_back", text=card["back"])
    else:
        side_text = get_text(lang, "flashcards_card_front", text=card["front"])
    
    text = get_text(lang, "flashcards_view_card", current=current, total=total, side=side_text)
    
    keyboard = get_flashcard_view_keyboard(set_id, card_id, current, total, is_flipped, lang)
    
    try:
        await message.edit_text(text, reply_markup=keyboard)
    except Exception:
        # If edit fails, send new message
        await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("flashcards_flip_"))
async def flip_card(callback: CallbackQuery):
    """Flip a flashcard"""
    parts = callback.data.split("_")
    set_id = parts[2]
    card_id = parts[3]
    current_state = int(parts[4])
    
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, callback.from_user.id)
        lang = user.interface_language.value
        
        if not mongo_service.is_ready():
            await callback.answer(get_text(lang, "error"), show_alert=True)
            return
        
        # Get the card
        card = await mongo_service.db().flashcards.find_one({"_id": ObjectId(card_id)})
        if not card:
            await callback.answer(get_text(lang, "error"), show_alert=True)
            return
        
        # Get position and total
        cards = await mongo_service.db().flashcards.find(
            {"set_id": set_id}
        ).sort("created_at", 1).to_list(length=1000)
        
        current = next((i + 1 for i, c in enumerate(cards) if str(c["_id"]) == card_id), 1)
        total = len(cards)
        
        # Toggle flip state
        is_flipped = not bool(current_state)
        
        await show_card(callback.message, set_id, card, current, total, is_flipped, lang)
        await callback.answer()


@router.callback_query(F.data.startswith("flashcards_nav_"))
async def navigate_cards(callback: CallbackQuery):
    """Navigate between flashcards"""
    parts = callback.data.split("_")
    set_id = parts[2]
    target_position = int(parts[3])
    
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, callback.from_user.id)
        lang = user.interface_language.value
        
        if not mongo_service.is_ready():
            await callback.answer(get_text(lang, "error"), show_alert=True)
            return
        
        # Get all cards
        cards = await mongo_service.db().flashcards.find(
            {"set_id": set_id}
        ).sort("created_at", 1).to_list(length=1000)
        
        if not cards or target_position < 1 or target_position > len(cards):
            await callback.answer(get_text(lang, "error"), show_alert=True)
            return
        
        card = cards[target_position - 1]
        await show_card(callback.message, set_id, card, target_position, len(cards), False, lang)
        await callback.answer()


@router.callback_query(F.data.startswith("flashcards_delete_card_"))
async def delete_card(callback: CallbackQuery):
    """Delete a flashcard"""
    parts = callback.data.split("_")
    set_id = parts[3]
    card_id = parts[4]
    
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, callback.from_user.id)
        lang = user.interface_language.value
        
        if not mongo_service.is_ready():
            await callback.answer(get_text(lang, "error"), show_alert=True)
            return
        
        # Delete the card
        await mongo_service.db().flashcards.delete_one(
            {"_id": ObjectId(card_id), "user_id": callback.from_user.id}
        )
        
        # Check if there are more cards
        remaining_cards = await mongo_service.db().flashcards.find(
            {"set_id": set_id}
        ).sort("created_at", 1).to_list(length=1000)
        
        if remaining_cards:
            # Show next card or first card
            await show_card(callback.message, set_id, remaining_cards[0], 1, len(remaining_cards), False, lang)
        else:
            # No more cards, go back to set view
            text = get_text(lang, "flashcards_card_deleted")
            await callback.message.edit_text(text, reply_markup=get_flashcard_set_keyboard(set_id, lang, has_cards=False))
        
        await callback.answer(get_text(lang, "flashcards_card_deleted"))


@router.callback_query(F.data.startswith("flashcards_delete_set_"))
async def delete_set_confirm(callback: CallbackQuery):
    """Ask for confirmation before deleting a set"""
    set_id = callback.data.split("_")[-1]
    
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, callback.from_user.id)
        lang = user.interface_language.value
        
        if not mongo_service.is_ready():
            await callback.answer(get_text(lang, "error"), show_alert=True)
            return
        
        try:
            flashcard_set = await mongo_service.db().flashcard_sets.find_one(
                {"_id": ObjectId(set_id), "user_id": callback.from_user.id}
            )
            
            if not flashcard_set:
                await callback.answer(get_text(lang, "error"), show_alert=True)
                return
            
            text = get_text(lang, "flashcards_delete_set_confirm", name=flashcard_set["name"])
            await callback.message.edit_text(text, reply_markup=get_delete_set_confirm_keyboard(set_id, lang))
            await callback.answer()
            
        except Exception as e:
            await callback.answer(get_text(lang, "error"), show_alert=True)


@router.callback_query(F.data.startswith("flashcards_confirm_delete_"))
async def delete_set_execute(callback: CallbackQuery):
    """Execute deletion of a flashcard set and all its cards"""
    set_id = callback.data.split("_")[-1]
    
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, callback.from_user.id)
        lang = user.interface_language.value
        
        if not mongo_service.is_ready():
            await callback.answer(get_text(lang, "error"), show_alert=True)
            return
        
        try:
            # Delete all cards in the set
            await mongo_service.db().flashcards.delete_many({"set_id": set_id})
            
            # Delete the set itself
            await mongo_service.db().flashcard_sets.delete_one(
                {"_id": ObjectId(set_id), "user_id": callback.from_user.id}
            )
            
            text = get_text(lang, "flashcards_set_deleted")
            await callback.message.edit_text(text, reply_markup=get_flashcards_menu_keyboard(lang))
            await callback.answer()
            
        except Exception as e:
            await callback.answer(get_text(lang, "error"), show_alert=True)
