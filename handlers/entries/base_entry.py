import datetime

from aiogram.types import CallbackQuery, Message

from keyboards.main_kb import get_main_menu_keyboard
from utils.functions import send_reply


def build_main_menu_text(user) -> str:
    now = datetime.datetime.now().hour
    greeting = (
        "Доброе утро" if 5 <= now < 12 else
        "Добрый день" if 12 <= now < 18 else
        "Добрый вечер"
    )
    welcome_message = (
        "🏠 <b>Главное меню</b>\n\n "
        f"{greeting}, <b>{user.full_name or user.first_name or user.username or 'пользователь'}</b>!\n\n"
        "Выберите действие:"
    )
    return welcome_message

async def show_main_menu(event: Message | CallbackQuery, user) -> None:  # state: FSMContext
    """Показывает главное меню.

    Middleware гарантирует:
    пользователь существует / не заблокирован / телефон подтверждён / user уже загружен из БД и передан сюда"""

    # будущие уведомления / активности пользователя / данные поиска
    """
    data = await state.get_data()
    unread_notifications = data.get("unread_notifications", 0)
    if unread_notifications > 0:
        welcome_message += f"\n\n🔔 У вас {unread_notifications} непрочитанных уведомлений"

    # Обновляем информацию о последней активности пользователя
    if "user" in context.user_data:
        context.user_data["user"]["last_activity"] = datetime.datetime.now().timestamp()

    # Очищаем временные данные поиска
    if "global_search" in context.user_data:
        del context.user_data["global_search"]
    if "for_search" in context.user_data:
        del context.user_data["for_search"]
    """

    await send_reply(
        event,
        build_main_menu_text(user),
        markup=get_main_menu_keyboard(user)
    )