from aiogram import F
from aiogram.types import CallbackQuery, Message

from .router import auth_router

from .helpers_auth.texts import build_settings_text, build_notification_settings_text
from .helpers_auth.keyboards import build_settings_keyboard, build_notification_settings_keyboard

from utils.functions import send_or_edit


@auth_router.callback_query(F.data == "back_to_profile_settings")
@auth_router.callback_query(F.data == "profile_settings")
async def show_settings(callback: CallbackQuery) -> None:
    """Показывает экран настроек пользователя."""
    await callback.answer()

    await send_or_edit(callback, build_settings_text(), build_settings_keyboard())


@auth_router.callback_query(F.data == "settings_notifications")
async def show_notification_settings(event: Message | CallbackQuery) -> None:
    """Показывает экран настроек уведомлений (только inline)."""
    await event.answer()

    # 📌 заглушка - Получаем текущий статус уведомлений (по умолчанию True)
    notifications_enabled = True  # TODO: добавить в модель User поле notifications_enabled

    await send_or_edit(
        event,
        build_notification_settings_text(notifications_enabled),
        build_notification_settings_keyboard(notifications_enabled)
    )