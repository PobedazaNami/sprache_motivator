from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from bot.models.database import UserStatus, async_session_maker
from bot.services.database_service import UserService
from bot.services import mongo_service
from bot.services.redis_service import redis_service
from bot.locales.texts import get_text
from bot.config import settings

router = Router()


SCENARIO_LABELS = {
    "uk": [
        "🛒 В магазині", "🏥 У лікаря", "💼 На роботі",
        "👋 Знайомство", "💬 У переписці", "🚌 У транспорті",
        "🏠 Оренда житла", "📄 Документи", "📞 Дзвінок",
        "🔧 Побутова проблема",
    ],
    "ru": [
        "🛒 В магазине", "🏥 У врача", "💼 На работе",
        "👋 Знакомство", "💬 В переписке", "🚌 В транспорте",
        "🏠 Аренда жилья", "📄 Документы", "📞 Звонок",
        "🔧 Бытовая проблема",
    ],
}


async def _get_due_flashcard_count(user_id: int) -> int:
    if not mongo_service.is_ready():
        return 0
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    count = await mongo_service.db().flashcards.count_documents({
        "user_id": user_id,
        "$or": [
            {"srs_status": {"$exists": False}},
            {"srs_status": "new"},
            {"srs_next_review": {"$exists": False}},
            {"srs_next_review": {"$lte": now}},
        ],
    })
    return count


async def _get_total_flashcard_count(user_id: int) -> int:
    if not mongo_service.is_ready():
        return 0
    return await mongo_service.db().flashcards.count_documents({"user_id": user_id})


async def _get_route_completion(user_id: int) -> dict:
    """Get today's route completion status from Redis."""
    from datetime import datetime
    from zoneinfo import ZoneInfo
    today = datetime.now(ZoneInfo("Europe/Berlin")).strftime("%Y-%m-%d")
    key = f"daily_route:{user_id}:{today}"
    data = await redis_service.get(key)
    if data:
        import json
        return json.loads(data)
    return {"step1": False, "step2": False, "step3": False}


async def _save_route_completion(user_id: int, completion: dict):
    from datetime import datetime
    from zoneinfo import ZoneInfo
    import json
    today = datetime.now(ZoneInfo("Europe/Berlin")).strftime("%Y-%m-%d")
    key = f"daily_route:{user_id}:{today}"
    await redis_service.set(key, json.dumps(completion), ex=86400)


@router.message(F.text.in_([
    "🔥 Сьогоднішній маршрут", "🔥 Маршрут на сегодня"
]))
async def daily_route_menu(message: Message, state: FSMContext):
    """Show today's learning route with 3 steps."""
    await state.clear()
    await redis_service.clear_user_state(message.from_user.id)

    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, message.from_user.id)

        if user.status != UserStatus.APPROVED:
            return

        lang = user.interface_language.value
        completion = await _get_route_completion(user.id)
        due_cards = await _get_due_flashcard_count(user.id)
        total_cards = await _get_total_flashcard_count(user.id)

        # Build route message
        step1_icon = "✅" if completion.get("step1") else "1️⃣"
        step2_icon = "✅" if completion.get("step2") else "2️⃣"
        step3_icon = "✅" if completion.get("step3") else "3️⃣"

        steps_done = sum(1 for k in ["step1", "step2", "step3"] if completion.get(k))

        text = get_text(lang, "daily_route_title", done=steps_done) + "\n\n"

        # Step 1: Express Trainer
        text += f"{step1_icon} " + get_text(lang, "daily_route_step1") + "\n"

        # Step 2: Flashcards
        if total_cards == 0:
            text += f"{step2_icon} " + get_text(lang, "daily_route_step2_no_cards") + "\n"
        elif due_cards == 0:
            text += f"{step2_icon} " + get_text(lang, "daily_route_step2_no_due") + "\n"
        else:
            text += f"{step2_icon} " + get_text(lang, "daily_route_step2", count=due_cards) + "\n"

        # Step 3: Subtitle Trainer or fallback
        text += f"{step3_icon} " + get_text(lang, "daily_route_step3") + "\n"

        if steps_done == 3:
            text += "\n" + get_text(lang, "daily_route_complete")

        from bot.utils.keyboards import get_daily_route_keyboard
        await message.answer(text, reply_markup=get_daily_route_keyboard(lang, total_cards, due_cards, completion))


@router.callback_query(F.data == "route_step1")
async def route_step1_express(callback: CallbackQuery, state: FSMContext):
    """Step 1: Start an express trainer task and mark step as done."""
    await callback.answer()
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, callback.from_user.id)
        lang = user.interface_language.value

    # Mark step 1 as done
    completion = await _get_route_completion(callback.from_user.id)
    completion["step1"] = True
    await _save_route_completion(callback.from_user.id, completion)

    # Send express task
    from bot.handlers.express_trainer import send_express_task
    await send_express_task(callback.from_user.id, callback.message.bot, callback.message.chat.id)


@router.callback_query(F.data == "route_step2_cards")
async def route_step2_flashcards(callback: CallbackQuery, state: FSMContext):
    """Step 2: Open flashcards."""
    await callback.answer()
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, callback.from_user.id)
        lang = user.interface_language.value

    # Mark step 2 as done
    completion = await _get_route_completion(callback.from_user.id)
    completion["step2"] = True
    await _save_route_completion(callback.from_user.id, completion)

    webapp_url = settings.WEBAPP_URL
    from bot.utils.keyboards import get_flashcards_menu_keyboard
    await callback.message.answer(
        get_text(lang, "flashcards_menu"),
        reply_markup=get_flashcards_menu_keyboard(lang, webapp_url)
    )


@router.callback_query(F.data == "route_step2_create")
async def route_step2_create_cards(callback: CallbackQuery, state: FSMContext):
    """Step 2 fallback: CTA to create first cards."""
    await callback.answer()
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, callback.from_user.id)
        lang = user.interface_language.value

    webapp_url = settings.WEBAPP_URL
    from bot.utils.keyboards import get_flashcards_menu_keyboard
    await callback.message.answer(
        get_text(lang, "daily_route_cta_create_cards"),
        reply_markup=get_flashcards_menu_keyboard(lang, webapp_url)
    )


@router.callback_query(F.data == "route_step3_subtitle")
async def route_step3_subtitle(callback: CallbackQuery, state: FSMContext):
    """Step 3: Open subtitle trainer."""
    await callback.answer()
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, callback.from_user.id)
        lang = user.interface_language.value

    # Mark step 3 as done
    completion = await _get_route_completion(callback.from_user.id)
    completion["step3"] = True
    await _save_route_completion(callback.from_user.id, completion)

    webapp_url = settings.WEBAPP_URL
    from bot.utils.keyboards import get_subtitle_trainer_keyboard
    await callback.message.answer(
        get_text(lang, "subtitle_trainer_menu"),
        reply_markup=get_subtitle_trainer_keyboard(lang, webapp_url)
    )


@router.callback_query(F.data == "route_step3_express")
async def route_step3_express_fallback(callback: CallbackQuery, state: FSMContext):
    """Step 3 fallback: Extra express task instead of subtitle."""
    await callback.answer()
    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, callback.from_user.id)

    completion = await _get_route_completion(callback.from_user.id)
    completion["step3"] = True
    await _save_route_completion(callback.from_user.id, completion)

    from bot.handlers.express_trainer import send_express_task
    await send_express_task(callback.from_user.id, callback.message.bot, callback.message.chat.id)
