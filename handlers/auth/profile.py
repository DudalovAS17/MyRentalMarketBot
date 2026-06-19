from aiogram import F
from aiogram.types import Message, CallbackQuery

from .router import auth_router

from .helpers_auth.texts import build_profile_text, build_profile_stats_text, build_achievements_text
from .helpers_auth.keyboards import build_back_to_profile_keyboard
from utils.functions import send_or_edit
from keyboards.common import get_profile_keyboard


@auth_router.message(F.text == "👤 Профиль")
@auth_router.callback_query(F.data == "back_to_profile")
async def profile(event: Message | CallbackQuery, user) -> None:
    """Показать профиль пользователя"""
    if isinstance(event, CallbackQuery):
        await event.answer()

    await send_or_edit(event, build_profile_text(user), get_profile_keyboard())

# ────────────────────────────────────────────────── Кнопки Профиля ────────────────────────────────────────────────────
@auth_router.callback_query(F.data == "profile_stats")
#@auth_router.message(F.text == "📊 Статистика")
async def show_statistics(callback: CallbackQuery) -> None:
    """Показывает экран статистики пользователя"""
    await callback.answer()

    await send_or_edit(callback, build_profile_stats_text(), build_back_to_profile_keyboard())


@auth_router.callback_query(F.data == "achievements")
#@auth_router.message(F.text == "🏆 Достижения")
async def show_achievements(callback: CallbackQuery) -> None:
    """Показывает экран достижений пользователя"""
    await callback.answer()

    await send_or_edit(callback, build_achievements_text(), build_back_to_profile_keyboard())