from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from bot.config import settings
from bot.models.database import UserStatus, async_session_maker
from bot.services.database_service import UserService
from bot.locales.texts import get_text
from bot.utils.keyboards import get_subtitle_trainer_keyboard

router = Router()


@router.message(F.text.in_([
    "🎬 Тренажер відео", "🎬 Тренажёр видео"
]))
async def subtitle_trainer_menu(message: Message, state: FSMContext):
    """Show subtitle trainer menu."""
    await state.clear()

    async with async_session_maker() as session:
        user = await UserService.get_or_create_user(session, message.from_user.id)

        if user.status != UserStatus.APPROVED:
            return

        lang = user.interface_language.value
        text = get_text(lang, "subtitle_trainer_menu")
        webapp_url = settings.WEBAPP_URL
        await message.answer(text, reply_markup=get_subtitle_trainer_keyboard(lang, webapp_url))
