from aiogram import F
from aiogram.types import CallbackQuery, Message

from .router import auth_router

from .helpers_auth.texts import build_settings_text, build_notification_settings_text
from .helpers_auth.keyboards import build_settings_keyboard, build_notification_settings_keyboard

from utils.functions import send_or_edit
from utils.callbacks import  (PROFILE_SETTINGS, PROFILE_BACK_TO_SETTINGS, PROFILE_NOTIFICATIONS,
                              PROFILE_TOGGLE_NOTIF_OFF, PROFILE_TOGGLE_NOTIF_ON)


@auth_router.callback_query(F.data == PROFILE_BACK_TO_SETTINGS)
@auth_router.callback_query(F.data == PROFILE_SETTINGS)
async def show_settings(callback: CallbackQuery) -> None:
    """Показывает экран настроек пользователя."""
    await callback.answer()

    await send_or_edit(callback, build_settings_text(), build_settings_keyboard())


@auth_router.callback_query(F.data == PROFILE_NOTIFICATIONS)
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

# не реализована
@auth_router.callback_query(F.data.in_({PROFILE_TOGGLE_NOTIF_ON, PROFILE_TOGGLE_NOTIF_OFF}))
async def toggle_notification_settings(callback: CallbackQuery) -> None:
    """Обработать кнопку уведомлений, пока настройка не хранится в модели User."""
    await callback.answer("Настройки уведомлений пока не сохраняются", show_alert=True)

    notifications_enabled = True  # TODO: добавить в модель User поле notifications_enabled
    await send_or_edit(
        callback,
        build_notification_settings_text(notifications_enabled),
        build_notification_settings_keyboard(notifications_enabled),
    )