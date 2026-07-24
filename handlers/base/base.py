from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import CommandStart
from aiogram.exceptions import TelegramBadRequest

from handlers.base.helpers_base import (resolve_main_menu_action, normalize_menu_text, safe_answer_for_blocked,
                                        CANCELLED_TO_MAIN_MENU_TEXT, UNKNOWN_MAIN_MENU_TEXT)
from handlers.entries import show_main_menu, start_registration #, request_phone_confirmation
from services.category_service import CategoryService
from services.rental_service import RentalService
from services.support_service import SupportService
from services.user_service import UserService, StartAction

from keyboards.common import get_main_menu_keyboard
from texts_otP.base import LEGAL_TEXT, HELP_TEXT, build_unknown_command_text
from utils.callbacks import BACK_TO_MENU_CB, NOOP_CB

base_router = Router()

# TODO: Если у пользователя есть непрочитанные уведомления - сообщаем/показываем

# ─────────────────────────────────────────────── /start ───────────────────────────────────────────────────────────────
@base_router.message(CommandStart())
@base_router.message(F.text == "🏠 Главное меню")
async def start(message: Message, state: FSMContext, user_service: UserService) -> None:
    """Универсальная точка входа.

    - если клиента нет в базе — запускаем регистрацию;
    - если клиент заблокирован — показываем блокировку;
    - если всё хорошо — показываем главное меню клиента.
        Было: - если клиент не подтвердил телефон — просим контакт;
    - если всё хорошо — показываем главное меню клиента.

    Сейчас Телефон не блокирует просмотр каталога: номер запрашивают целевые сценарии вроде аренды и поддержки.
    """

    await state.clear()

    tg_id = message.from_user.id
    result = await user_service.resolve_start_entry(tg_id)

    if message.from_user is None:
        await message.answer("⚠️ Не удалось определить пользователя Telegram. Попробуйте открыть меню через /start ещё раз.")
        return None

    # Если новый — регистрируем
    if result.action == StartAction.REGISTER:
        return await start_registration(message, user_service)

    # # Если пользователь уже есть, но телефон ещё не подтверждён — повторно показываем кнопку контакта
    # if result.action == StartAction.NEED_PHONE:
    #     return await request_phone_confirmation(message)

    # Проверяем блокировку
    if result.action == StartAction.ACCESS_BLOCKED:
        return await safe_answer_for_blocked(message)

    # ✅ Приветствие
    return await show_main_menu(message, result.user)

@base_router.callback_query(F.data.startswith(BACK_TO_MENU_CB))
async def show_main_menu_callback(callback: CallbackQuery, user) -> None:
    """Показать главное меню по callback-кнопке"""
    await callback.answer()

    try: # NEW
        #await callback.message.delete()
        if isinstance(callback.message, Message):
            await callback.message.delete()
    except TelegramBadRequest:
        pass

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

    await state.clear()
    await message.answer(CANCELLED_TO_MAIN_MENU_TEXT)

    return await show_main_menu(message, user)

@base_router.message(F.text.startswith("/"))
async def unknown_command(message: Message) -> None:
    """Отвечает на неизвестную команду."""
    command = message.text
    await message.answer(build_unknown_command_text(command), reply_markup=get_main_menu_keyboard())

@base_router.callback_query(F.data == NOOP_CB)
async def noop(callback) -> None:
    """Закрыть callback-заглушку."""
    await callback.answer("Недоступно", show_alert=False)


# ───────────────────────────────────────────────── TextMessageHandler ─────────────────────────────────────────────────
@base_router.message(F.text)
async def text_message_handler(
        message: Message,
        state: FSMContext,
        category_service: CategoryService,
        rental_service: RentalService,
        support_service: SupportService,
        user
) -> None:
    """Обрабатывает текстовые сообщения от клиента в главном меню.

    - определяет по тексту, что пользователь хотел
    - вызывает нужный сценарий (handler-функцию)
    """
    text = normalize_menu_text(message.text)
    action = resolve_main_menu_action(message, state, category_service, rental_service, support_service, user=user, text=text)

    # Если текст не соответствует ни одной кнопке
    if action is None:
        await message.answer(UNKNOWN_MAIN_MENU_TEXT)
        return

    await action()