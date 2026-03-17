import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import CommandStart

from services.category_service import CategoryService
from services.item_service import ItemService
from services.user_service import UserService
from services.use_case.user import StartAction

from handlers.entries.category_entry import show_categories
from handlers.item.show import show_my_items
from handlers.item.flow_create import start_create_item_from_menu
from handlers.search import start_search
from handlers.entries.base_entry import show_main_menu
from handlers.support import support_start

from keyboards.main_kb import get_main_menu_keyboard
from texts.base import LEGAL_TEXT, HELP_TEXT, build_unknown_command_text

logger = logging.getLogger(__name__)
base_router = Router()
support_router = Router()

"""
Локально в handler / entrypoint ловим только ожидаемые и сценарные ошибки. Например,
    IntegrityError как мягкий дубль регистрации;
    ServiceError, если сервис специально бросает бизнесовую ошибку.
"""

"""
 - /start и "🏠 Главное меню"
 - "menu:main" / "back_to_main_menu"
 - /help
 - /legal
 - /cancel
 - / (unknown_command)
 - "noop"
 - text_message_handler
"""

@base_router.message(CommandStart())
@base_router.message(F.text == "🏠 Главное меню") # ?
async def start(message: Message, state: FSMContext, user_service: UserService):
    """Универсальная точка входа.
    - Если пользователя нет — запускает регистрацию.
    - Если есть — приветствует и показывает главное меню"""

    # Если пользователь когда-то застрял в регистрации, aiogram может оставить старое состояние FSM
    # 🧹 очищаем старое состояние FSM, чтобы бот всегда начинает “с чистого листа”
    await state.clear()

    tg_id = message.from_user.id
    result = await user_service.resolve_start_entry(tg_id)

    # Если новый — регистрируем
    if result.action == StartAction.REGISTER: # Логика "Если нет телефона" - отдельно не обрабатывается
        logger.info(f"[/start] Новый пользователь {tg_id} → переход к регистрации")
        from handlers.entries.auth_entry import start_registration
        return await start_registration(message, user_service)

    # Пользователь найден, проверяем блокировку
    if result.action == StartAction.ACCESS_BLOCKED:
        return await safe_answer_for_blocked(message)

    # ✅ Приветствие
    return await show_main_menu(message, result.user)

@base_router.callback_query(F.data.in_(["menu:main", "back_to_main_menu"]))
async def show_main_menu_callback(callback: CallbackQuery, user):
    await callback.answer()
    await show_main_menu(callback, user)

# ─────────────────────────────────────────────────Commands─────────────────────────────────────────────────────────────
@base_router.message(F.text == "/help")
async def help_command(message: Message):
    """Помощь"""
    await message.answer(HELP_TEXT)

@base_router.message(F.text == "/legal")
async def legal_command(message: Message) -> None:
    """Отправляет юридическую информацию при команде /legal."""
    await message.answer(LEGAL_TEXT)

@base_router.message(F.text == "/cancel")
async def cancel(message: Message, state: FSMContext, user):
    """Отмена операции, возврат в главное меню"""
    tg_id = message.from_user.id
    logger.info(f"Пользователь %s отменил текущую операцию", tg_id)

    """ Выкинули это:
    Если это была операция создания объявления, сообщаем пользователю,
    что его черновик сохранен для будущего использования
    """

    # Очищаем временные данные/ключи - "for_search", "item_data", "search_filters", "search_city" и тп
    await state.clear() # удаляет и состояние, и все данные FSM - все ключи удаляются

    await message.answer("❌ Операция отменена. Возвращаемся в главное меню 🏠")
    return await show_main_menu(message, user)

@base_router.message(F.text.startswith("/"))
async def unknown_command(message: Message, user): # state: FSMContext
    """Отвечает на неизвестную команду."""
    command = message.text
    reply_text = build_unknown_command_text(command)
    await message.answer(reply_text, reply_markup=get_main_menu_keyboard(user))

@base_router.callback_query(F.data == "noop")
async def noop(callback):
    await callback.answer("Недоступно", show_alert=False)

# ─────────────────────────────────────────────────text_message_handler─────────────────────────────────────────────────
def _resolve_main_menu_action(
    *,
    text: str,
    message: Message,
    state: FSMContext,
    category_service: CategoryService,
    item_service: ItemService,
    user,
):
    """ Определяет команды на основе текста сообщения и вызывает соответствующий обработчик"""

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
        "📦 Мои объявления": lambda: show_my_items(message, item_service),
        "🔎 Поиск": lambda: start_search(message, state),
        # "📱 Изменить номер": lambda: request_phone_number_change(message, state),

        # Служебные разделы
        # "👤 Профиль": lambda: profile(message, user_service),
        # "📋 Мои сделки": lambda: view_my_rentals(message, state),
        # "⚙️ Настройки": lambda: show_settings(state),
        # "📊 Статистика": lambda: show_statistics(state),
        # "🏆 Достижения": lambda: show_achievements(state),

        # Системные действия
        "❓ Помощь": lambda: help_command(message),
        "⬅️ Вернуться в меню": lambda: show_main_menu(message, user),  # user_service,
    }

    return routes.get(text)

@base_router.message(F.text)
async def text_message_handler(
    message: Message,
    state: FSMContext,
    category_service: CategoryService,
    item_service: ItemService,
    user
):
    """Обрабатывает текстовые сообщения от пользователя в главном меню.

    - определяет по тексту (или по ID кнопки), что пользователь хотел;
    - вызывает нужный сценарий (handler-функцию)
    """
    text = _normalize_menu_text(message.text)

    action = _resolve_main_menu_action(
        text=text,
        message=message,
        state=state,
        category_service=category_service,
        item_service=item_service,
        user=user,
    )

    # Если текст не соответствует ни одной кнопке
    if action is None:
        #logger.warning(f"Неопознанный текст от пользователя {user.id}: '{text}'")
        await message.answer("❓ Неизвестная команда. Используйте меню для навигации.")
        return

    await action()

# ─────────────────────────────────────────────────helpers──────────────────────────────────────────────────────────────
BLOCKED_ACCOUNT_TEXT = "⚠️ Ваша учётная запись заблокирована. Пожалуйста, обратитесь в службу поддержки."
async def safe_answer_for_blocked(message: Message):
    await message.answer(BLOCKED_ACCOUNT_TEXT)

def _normalize_menu_text(text: str | None) -> str:
    return text.strip() if text else ""