from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from handlers.entries import show_main_menu
from handlers.support.helpers_support import (render_admin_ticket_message, build_support_request_text, build_support_confirmation_text,
                             build_support_cancel_keyboard, build_support_already_open_text, notify_admins,
                             build_support_already_open_after_create_text)
from services.support_service import SupportService, TicketAlreadyOpen

from states.support_ticket import SupportStates
from schemas.support import SupportTicketCreateInternal
from utils.functions import send_or_edit

"""создание тикета + отправка админам"""
support_router = Router()

# ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
# если хочешь reply-кнопку в меню — добавишь "Поддержка"
@support_router.message(Command("support"))
async def support_start(message: Message, state: FSMContext, support_service: SupportService, user) -> None:
    """Старт поддержки через команду /support."""
    await start_support_flow(message, state, support_service, user)

@support_router.callback_query(F.data == "support:start")
async def support_start_callback(callback: CallbackQuery, state: FSMContext, support_service: SupportService, user) -> None:
    """Старт поддержки через кнопку."""
    await callback.answer()

    await start_support_flow(callback, state, support_service, user)


# ──────────────────────────────────────────────── FSM-поддержки ───────────────────────────────────────────────────────
async def start_support_flow(event: Message | CallbackQuery, state: FSMContext, support_service: SupportService, user) -> None:
    """Единый вход в поддержку"""

    open_ticket = await support_service.get_open_ticket_by_user(user.id)
    if open_ticket:
        await send_or_edit(event, build_support_already_open_text(open_ticket.id), None)
        return

    await state.set_state(SupportStates.waiting_text)

    await send_or_edit(event, build_support_request_text(), build_support_cancel_keyboard()) # None

@support_router.message(SupportStates.waiting_text, F.text)
async def receive_support_text(
    message: Message,
    state: FSMContext,
    support_service: SupportService,
    user,
    admin_ids: list[int],
) -> None:
    """Обрабатывает сообщение пользователя для службы поддержки. Создание тикета и отправка уведомления админам."""

    text = (message.text or "").strip()
    if not text:
        await send_or_edit(message, "❌ Текст не может быть пустым. Пожалуйста, отправьте текст обращения.")
        return

    try:
        internal = SupportTicketCreateInternal(
                user_id=user.id,
                #telegram_id=int(user.telegram_id),
                username=user.username,
                text=text,
            )
        ticket = await support_service.create(ticket_data=internal)
    except TicketAlreadyOpen as exc:
        await state.clear()
        await send_or_edit(message, build_support_already_open_after_create_text(exc.ticket_id))
        return

    # Завершаем сценарий поддержки
    await state.clear()

    # Отправляем подтверждение пользователю
    await send_or_edit(message, build_support_confirmation_text())

    # отправляем сообщение поддержки админу
    await notify_admins(message.bot, admin_ids, render_admin_ticket_message(ticket, user), ticket.id)

    # Возвращаем пользователя в главное меню
    # await show_main_menu(message, user)


# ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
@support_router.callback_query(F.data == "support:cancel") # "cancel_support"
async def cancel_support(callback: CallbackQuery, state: FSMContext, user) -> None:
    """Отменить обращение в поддержку."""
    await callback.answer()

    await state.clear()
    await callback.message.answer("❌ Обращение в поддержку отменено.")

    # Возвращаем пользователя в главное меню
    await show_main_menu(callback, user)