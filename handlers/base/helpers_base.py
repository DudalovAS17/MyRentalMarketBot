from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.exceptions import TelegramBadRequest
from collections.abc import Awaitable, Callable

from handlers.entries import show_main_menu, show_categories, show_my_rentals
from handlers.search.search import start_search
from handlers.support.support import support_start
from services.category_service import CategoryService
from services.rental_service import RentalService
from services.support_service import SupportService

from keyboards.common import build_faq_sections_keyboard, build_info_page_keyboard
from texts_otP.info_pages import FAQ_MENU_TEXT, INFO_MENU_TEXTS

# ────────────────────────────────────────────────── Texts ─────────────────────────────────────────────────────────────
BLOCKED_ACCOUNT_TEXT = "⚠️ Ваша учётная запись заблокирована. Пожалуйста, обратитесь в службу поддержки."
CANCELLED_TO_MAIN_MENU_TEXT = "❌ Операция отменена. Возвращаемся в главное меню 🏠"
UNKNOWN_MAIN_MENU_TEXT = "❓ Неизвестная команда. Используйте меню для навигации."

async def safe_answer_for_blocked(message: Message) -> None:
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
    support_service: SupportService,
    user,
    text: str,
    #help_command,
) -> MenuAction | None:
    """Определяет действие по тексту кнопки главного меню."""

    if not text:
        return None

    if text == "❓ FAQ":
        return lambda: show_faq_sections(message)

    if text in INFO_MENU_TEXTS:
        return lambda: show_info_menu_text(message, INFO_MENU_TEXTS[text])

    # 🧭 маршрутизация
    routes = {
        "🛠 Каталог товаров": lambda: show_categories(message, category_service),
        "🔎 Поиск оборудования": lambda: start_search(message, state),
        "📋 Мои аренды": lambda: show_my_rentals(message, rental_service, user),
        "📋 Мои заявки": lambda: show_my_rentals(message, rental_service, user),
        #"👤 Профиль": lambda: profile(message, user_service),
        "📞 Связаться с менеджером": lambda: support_start(message, state, support_service, user), # "📞 Поддержка"
        #"❓ Помощь": lambda: help_command(message),
        "⬅️ Вернуться в меню": lambda: show_main_menu(message, user),
        "🏠 Главное меню": lambda: show_main_menu(message, user),
    }

    return routes.get(text)

# ─────────────────────────────────────────────── Helpers ──────────────────────────────────────────────────────────────
async def cleanup_menu_transition_messages(message: Message) -> None:
    """Убрать старое меню и нажатую reply-кнопку, чтобы не плодить сообщения."""
    for message_id in (message.message_id - 1, message.message_id):
        if message_id <= 0:
            continue
        try:
            await message.bot.delete_message(chat_id=message.chat.id, message_id=message_id)
        except TelegramBadRequest:
            pass

async def show_faq_sections(message: Message) -> None:
    """Показать меню разделов FAQ."""
    await cleanup_menu_transition_messages(message)
    await message.answer(FAQ_MENU_TEXT, reply_markup=build_faq_sections_keyboard())

async def show_info_menu_text(message: Message, text: str) -> None:
    """Показать простой информационный текст из главного меню."""
    await cleanup_menu_transition_messages(message)
    await message.answer(text, reply_markup=build_info_page_keyboard())