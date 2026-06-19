from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from collections.abc import Awaitable, Callable

from handlers.entries import show_main_menu, show_categories, show_my_rentals
from handlers.search.search import start_search
from handlers.support.support import support_start
from services.category_service import CategoryService
from services.rental_service import RentalService

# ────────────────────────────────────────────────── Texts ─────────────────────────────────────────────────────────────
BLOCKED_ACCOUNT_TEXT = "⚠️ Ваша учётная запись заблокирована. Пожалуйста, обратитесь в службу поддержки."
CANCELLED_TO_MAIN_MENU_TEXT = "❌ Операция отменена. Возвращаемся в главное меню 🏠"
UNKNOWN_MAIN_MENU_TEXT = "❓ Неизвестная команда. Используйте меню для навигации."

async def safe_answer_for_blocked(message: Message):
    """Сообщить пользователю, что его аккаунт заблокирован."""
    await message.answer(BLOCKED_ACCOUNT_TEXT)

# ─────────────────────────────────────────────── Validation ───────────────────────────────────────────────────────────
def normalize_menu_text(text: str | None) -> str:
    """Нормализовать текст кнопки главного меню."""
    return text.strip() if text else ""

# ────────────────────────────────────── маршрутизация главного меню ───────────────────────────────────────────────────
MenuAction = Callable[[], Awaitable[None]]
def resolve_main_menu_action(
    message: Message,
    state: FSMContext,
    category_service: CategoryService,
    rental_service: RentalService,
    user,
    text: str,
    #help_command,
) -> MenuAction | None:
    """Определяет действие по тексту кнопки главного меню."""

    if not text:
        return None

    # 🧭 маршрутизация
    routes = {
        "🔍 Арендовать": lambda: show_categories(message, category_service),
        "🔎 Поиск": lambda: start_search(message, state),
        "📞 Поддержка": lambda: support_start(message, state), # start_support_dialog
        #"❓ Помощь": lambda: help_command(message),
        "⬅️ Вернуться в меню": lambda: show_main_menu(message, user),
        "🏠 Главное меню": lambda: show_main_menu(message, user),

        # Служебные разделы
        #"👤 Профиль": lambda: profile(message, user_service),
        "📋 Мои сделки": lambda: show_my_rentals(message, rental_service, user),
    }

    return routes.get(text)


# Служебные разделы - сюда будет доступ не по текстам, а только через кнопки:
# "⚙️ Настройки": lambda: show_settings(state),
# "📊 Статистика": lambda: show_statistics(state),
# "🏆 Достижения": lambda: show_achievements(state),

#from handlers.item.flow_create import start_create_item_from_menu
#from handlers.item.show import show_my_items
# "📦 Сдать в аренду": lambda: start_create_item_from_menu(message, state, user),
# "📦 Мои объявления": lambda: show_my_items(message, item_service, user),

# "📱 Изменить номер": lambda: request_phone_number_change(message, state),

# 🔔 Уведомления — отдельная ветка (не FSM)
#if text.startswith("🔔 Уведомления"):
    #return lambda: show_notification_settings(message, state)