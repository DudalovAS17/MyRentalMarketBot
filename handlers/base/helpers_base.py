from __future__ import annotations

from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from handlers.entries.base_entry import show_main_menu
from handlers.entries.category_entry import show_categories
from handlers.item.flow_create import start_create_item_from_menu
from handlers.item.show import show_my_items
from handlers.search import start_search
from handlers.support import support_start
from services.category_service import CategoryService
from services.item_service import ItemService


BLOCKED_ACCOUNT_TEXT = "⚠️ Ваша учётная запись заблокирована. Пожалуйста, обратитесь в службу поддержки."
CANCELLED_TO_MAIN_MENU_TEXT = "❌ Операция отменена. Возвращаемся в главное меню 🏠"
UNKNOWN_MAIN_MENU_TEXT = "❓ Неизвестная команда. Используйте меню для навигации."

async def safe_answer_for_blocked(message: Message):
    await message.answer(BLOCKED_ACCOUNT_TEXT)

def normalize_menu_text(text: str | None) -> str:
    """Нормализовать текст кнопки главного меню."""
    return text.strip() if text else ""


def resolve_main_menu_action(
    message: Message,
    state: FSMContext,
    category_service: CategoryService,
    item_service: ItemService,
    user,
    text: str,
    #help_command,
):
    """Определяет действие по тексту кнопки главного меню."""

    if not text:
        return None

    # 📞 Поддержка — особая логика (отдельное состояние FSM)
    if text == "📞 Поддержка":
        return lambda: support_start(message, state)

    # 🔔 Уведомления — отдельная ветка (не FSM)
    #if text.startswith("🔔 Уведомления"):
        #return lambda: show_notification_settings(message, state)

    # 🧭 Основная маршрутизация (кнопка -> действие)
    routes = {
        # FSM-сценарии
        # "📞 Поддержка": lambda: start_support_dialog(message, state)
        "🔍 Арендовать": lambda: show_categories(message, category_service),
        "📦 Сдать в аренду": lambda: start_create_item_from_menu(message, state, user),
        "📦 Мои объявления": lambda: show_my_items(message, item_service, user),
        "🔎 Поиск": lambda: start_search(message, state),
        # "📱 Изменить номер": lambda: request_phone_number_change(message, state),

        # Служебные разделы
        # "👤 Профиль": lambda: profile(message, user_service),
        # "📋 Мои сделки": lambda: view_my_rentals(message, state),
        # "⚙️ Настройки": lambda: show_settings(state),
        # "📊 Статистика": lambda: show_statistics(state),
        # "🏆 Достижения": lambda: show_achievements(state),

        # Системные действия
        #"❓ Помощь": lambda: help_command(message),
        "⬅️ Вернуться в меню": lambda: show_main_menu(message, user),  # user_service,
    }

    return routes.get(text)
