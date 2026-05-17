from aiogram import F
from aiogram.types import CallbackQuery

from .router import auth_router

from .helpers_auth.texts import build_privacy_policy_text, build_privacy_settings_text
from .helpers_auth.keyboards import build_privacy_policy_keyboard, build_privacy_settings_keyboard

from utils.functions import send_or_edit

@auth_router.callback_query(F.data == "settings_privacy")
async def show_privacy_settings(callback: CallbackQuery) -> None:
    """Показывает экран настроек конфиденциальности."""
    await callback.answer()

    await send_or_edit(callback, build_privacy_settings_text(), build_privacy_settings_keyboard())


@auth_router.callback_query(F.data == "show_privacy_policy")
async def send_privacy_policy(callback: CallbackQuery) -> None:
    """Показывает текст политики конфиденциальности"""
    await callback.answer()

    await send_or_edit(callback, build_privacy_policy_text(), build_privacy_policy_keyboard())