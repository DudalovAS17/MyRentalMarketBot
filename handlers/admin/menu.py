import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from .admin_helpers.keyboard  import get_admin_menu_keyboard, get_back_to_admin_menu_keyboard
from utils.functions import send_or_edit

logger = logging.getLogger(__name__)

admin_menu_router = Router()

"""
Интерфейсы
    - рассылки сообщений
    - модерации объявлений
    - управления пользователями

Статистику использования бота
Настройки бота

"""

ADMIN_MENU_TEXT = (
    "🛡️ <b>Админ-панель</b>\n\n"
    "Выберите раздел управления:"
)

@admin_menu_router.message(Command("admin"))
@admin_menu_router.callback_query(F.data == "admin:menu")
async def show_admin_menu(event: Message | CallbackQuery, user) -> None:
    """Точка входа в админку (/admin)."""
    logger.info("[Admin] User %s opened admin menu", user.id)
    await send_or_edit(event, ADMIN_MENU_TEXT, markup=get_admin_menu_keyboard(), parse_mode="HTML")

# ?
@admin_menu_router.callback_query(F.data == "admin:exit")
async def admin_exit(callback: CallbackQuery): # , user
    """Выход из админки.

    - либо возвращаем в show_main_menu
    - либо просто пишем "возврат в меню" и даём кнопку.
    """
    await send_or_edit(callback, "✅ Вы вышли из админки.", get_back_to_admin_menu_keyboard(), parse_mode="HTML")
    await callback.answer()

# "admin:menu"
# admin_menu - Показать главное меню админки.

# "admin:content" - "Контент/FAQ"