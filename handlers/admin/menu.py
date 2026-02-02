from __future__ import annotations
import logging

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from states.admin import AdminStates
from keyboards.admin_kb import (
    get_admin_deals_list_keyboard,
    get_admin_deal_details_keyboard,
)

from services.admin_rental_service import AdminRentalService

from keyboards.admin_kb import get_admin_menu_keyboard, get_back_to_admin_menu_keyboard, get_admin_dispute_target_keyboard
from utils.functions import send_or_edit

logger = logging.getLogger(__name__)
admin_menu_router = Router()

ADMIN_MENU_TEXT = (
    "🛡️ <b>Админ-панель</b>\n\n"
    "Выберите раздел управления:"
)

# Показывает интерфейс рассылки сообщений.
# Показывает настройки бота.
# Показывает интерфейс модерации объявлений.
# Показывает интерфейс управления пользователями.
# Показывает статистику использования бота.

@admin_menu_router.message(Command("admin"))
@admin_menu_router.callback_query(F.data == "admin:menu")
async def show_admin_menu(event: Message | CallbackQuery, user) -> None:
    """Точка входа в админку (/admin)."""
    logger.info("[Admin] User %s opened admin menu", user.id)
    await send_or_edit(event, ADMIN_MENU_TEXT, markup=get_admin_menu_keyboard()) # , parse_mode="HTML"

#@admin_menu_router.message(Command("admin"))
#async def admin_entry(message: Message, user) -> None:
#    """Точка входа в админку (/admin)."""
#    await send_or_edit(message, ADMIN_MENU_TEXT, get_admin_menu_keyboard(), parse_mode="HTML")

#@admin_menu_router.callback_query(F.data == "admin:menu")
#async def admin_menu(callback: CallbackQuery, user) -> None:
#    """Показать главное меню админки."""
#    await send_or_edit(callback, ADMIN_MENU_TEXT, get_admin_menu_keyboard(), parse_mode="HTML")
#    await callback.answer()


@admin_menu_router.callback_query(F.data == "admin:exit")
async def admin_exit(callback: CallbackQuery, user):
    """
    Выход из админки.
    Тут логика зависит от твоего главного меню:
    - либо возвращаем в show_main_menu
    - либо просто пишем "возврат в меню" и даём кнопку.
    """
    await send_or_edit(
        callback,
        "✅ Вы вышли из админки.",
        get_back_to_admin_menu_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


# --- Разделы (пока заглушки) ---
async def _show_admin_placeholder(callback: CallbackQuery, title: str) -> None:
    await callback.answer()
    text = f"🧩 Раздел «{title}» в разработке.\n\n Вернитесь в админ-меню."
    await send_or_edit(
        callback,
        text,
        markup=get_back_to_admin_menu_keyboard(),  # временно, можно заменить на главное меню
        parse_mode="HTML",
    )

#@admin_menu_router.callback_query(F.data == "admin:deals")
#async def admin_deals(callback: CallbackQuery, user) -> None:
#    await _show_admin_placeholder(callback, "Сделки")


#@admin_menu_router.callback_query(F.data == "admin:items")
#async def admin_items(callback: CallbackQuery, user) -> None:
#    await _show_admin_placeholder(callback, "Объявления")


#@admin_menu_router.callback_query(F.data == "admin:users")
#async def admin_users(callback: CallbackQuery, user) -> None:
#    await _show_admin_placeholder(callback, "Пользователи")


@admin_menu_router.callback_query(F.data == "admin:disputes")
async def admin_disputes(callback: CallbackQuery, user) -> None:
    await _show_admin_placeholder(callback, "Жалобы/споры")


#@admin_menu_router.callback_query(F.data == "admin:support")
#async def admin_support(callback: CallbackQuery, user) -> None:
#    await _show_admin_placeholder(callback, "Поддержка")


@admin_menu_router.callback_query(F.data == "admin:content")
async def admin_content(callback: CallbackQuery, user) -> None:
    await _show_admin_placeholder(callback, "Контент/FAQ")
