from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from handlers.entries import show_main_menu
from handlers.admin.notify import notify_admins
from handlers.support.helpers_support import (render_admin_ticket_message, build_support_request_text, build_support_confirmation_text,
                             build_support_cancel_keyboard, build_support_already_open_text,
                             build_support_already_open_after_create_text) # notify_admins,
from services.support_service import SupportService, TicketAlreadyOpen
from services.rental_service import RentalService

from states.support_ticket import SupportStates
from schemas.support import SupportTicketCreateInternal
from utils.functions import send_or_edit
from utils.callbacks import CLIENT_SUPPORT_RENTAL_CB
from utils.errors import ServiceError

"""создание тикета + отправка админам"""
support_router = Router()

# ***** кнопка админки "Обращения клиентов" *****

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

@support_router.callback_query(F.data.startswith(CLIENT_SUPPORT_RENTAL_CB))
async def support_start_rental_callback(
    callback: CallbackQuery,
    state: FSMContext,
    support_service: SupportService,
    rental_service: RentalService,
    user,
) -> None:
    """Старт поддержки из карточки клиентской заявки на аренду."""
    await callback.answer()

    raw_rental_id = (callback.data or "").removeprefix(CLIENT_SUPPORT_RENTAL_CB)
    try:
        rental_id = int(raw_rental_id)
    except ValueError:
        await callback.answer("Некорректная заявка.", show_alert=True)
        return

    try:
        details = await rental_service.get_rental_details(rental_id=rental_id, current_user_id=user.id)
    except ServiceError:
        await callback.answer("Ошибка. Попробуйте позже.", show_alert=True)
        return

    if details is None:
        await callback.answer("Заявка не найдена или нет доступа.", show_alert=True)
        return

    await start_support_flow(callback, state, support_service, user, rental_id=rental_id)


# ──────────────────────────────────────────────── FSM-поддержки ───────────────────────────────────────────────────────
async def start_support_flow(
        event: Message | CallbackQuery,
        state: FSMContext,
        support_service: SupportService,
        user,
        *,
        rental_id: int | None = None,
) -> None:
    """Единый вход в поддержку"""

    open_ticket = await support_service.get_open_ticket_by_user(user.id)
    if open_ticket:
        await send_or_edit(event, build_support_already_open_text(open_ticket.id), None)
        return

    await state.set_state(SupportStates.waiting_text)
    await state.update_data(support_rental_id=rental_id) # ???

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

    data = await state.get_data()
    rental_id = data.get("support_rental_id")

    try:
        internal = SupportTicketCreateInternal(
                user_id=user.id,
                #telegram_id=int(user.telegram_id),
                #username=user.username,
                text=text,
                subject=f"Заявка на аренду #{rental_id}" if rental_id else None,
                rental_id=rental_id,
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