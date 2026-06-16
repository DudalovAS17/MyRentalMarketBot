from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import CommandStart

from handlers.base.helpers_base import (resolve_main_menu_action, normalize_menu_text, safe_answer_for_blocked,
                                        CANCELLED_TO_MAIN_MENU_TEXT, UNKNOWN_MAIN_MENU_TEXT)
from handlers.entries.base_entry import show_main_menu
from handlers.entries.auth_entry import start_registration

from services.category_service import CategoryService
from services.item_service import ItemService
from services.user_service import UserService, StartAction

from keyboards.main_kb import get_main_menu_keyboard
from texts.base import LEGAL_TEXT, HELP_TEXT, build_unknown_command_text

base_router = Router()

# ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
@base_router.message(CommandStart())
@base_router.message(F.text == "🏠 Главное меню")
async def start(message: Message, state: FSMContext, user_service: UserService) -> None:
    """Универсальная точка входа.

    - Если пользователя нет — запускает регистрацию.
    - Если есть — приветствует и показывает главное меню"""

    await state.clear()

    tg_id = message.from_user.id
    result = await user_service.resolve_start_entry(tg_id)

    # Если новый — регистрируем
    if result.action == StartAction.REGISTER:
        return await start_registration(message, user_service)

    # Проверяем блокировку
    if result.action == StartAction.ACCESS_BLOCKED:
        return await safe_answer_for_blocked(message)

    # ✅ Приветствие
    return await show_main_menu(message, result.user)

@base_router.callback_query(F.data.in_(["menu:main", "back_to_main_menu"]))
async def show_main_menu_callback(callback: CallbackQuery, user) -> None:
    """Показать главное меню по callback-кнопке"""
    await callback.answer()

    await show_main_menu(callback, user)


# ──────────────────────────────────────────────── Commands ────────────────────────────────────────────────────────────
@base_router.message(F.text == "/help")
async def help_command(message: Message) -> None:
    """Показать помощь."""
    await message.answer(HELP_TEXT)

@base_router.message(F.text == "/legal")
async def legal_command(message: Message) -> None:
    """Показать юридическую информацию."""
    await message.answer(LEGAL_TEXT)

@base_router.message(F.text == "/cancel")
async def cancel(message: Message, state: FSMContext, user) -> None:
    """Пользователь отменил текущую операцию - возврат в главное меню."""

    # TODO: если отменено создание объявления - сообщение пользователю: черновик сохранен для будущего использования

    await state.clear()
    await message.answer(CANCELLED_TO_MAIN_MENU_TEXT)

    return await show_main_menu(message, user)

@base_router.message(F.text.startswith("/"))
async def unknown_command(message: Message, user) -> None:
    """Отвечает на неизвестную команду."""
    command = message.text
    await message.answer(build_unknown_command_text(command), reply_markup=get_main_menu_keyboard(user))

@base_router.callback_query(F.data == "noop")
async def noop(callback) -> None:
    """Закрыть callback-заглушку."""
    await callback.answer("Недоступно", show_alert=False)


# ───────────────────────────────────────────────── TextMessageHandler ─────────────────────────────────────────────────
@base_router.message(F.text)
async def text_message_handler(
        message: Message,
        state: FSMContext,
        category_service: CategoryService,
        item_service: ItemService,
        user
) -> None:
    """Обрабатывает текстовые сообщения от пользователя в главном меню.

    - определяет по тексту (или по ID кнопки), что пользователь хотел
    - вызывает нужный сценарий (handler-функцию)
    """
    text = normalize_menu_text(message.text)
    action = resolve_main_menu_action(message, state, category_service, item_service, user=user, text=text)

    # Если текст не соответствует ни одной кнопке
    if action is None:
        await message.answer(UNKNOWN_MAIN_MENU_TEXT)
        return

    await action()