from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from handlers.entries import show_main_menu
from handlers.support.helpers_support import (build_support_request_text, build_support_cancel_keyboard,
                                              build_support_already_open_text, build_support_already_open_after_create_text,
                                              build_support_continue_keyboard)
from handlers.admin.admin_helpers.keyboard import get_admin_support_ticket_notification_keyboard
from services.support_service import SupportService, TicketAlreadyOpen
from services.item_service import ItemService
from services.rental_service import RentalService
from services.notif_service import NotificationService

from states.support_ticket import SupportStates
from schemas.support import SupportTicketCreateInternal
from utils.functions import send_or_edit
from utils.callbacks import CLIENT_SUPPORT_RENTAL_CB, SUPPORT, SUPPORT_START, SUPPORT_CANCEL, MESSAGE_OWNER_CB, SUPPORT_CONTINUE
from utils.errors import ServiceError

"""создание тикета + отправка админам"""
support_router = Router()

# ***** кнопка админки "Обращения клиентов" *****

# ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
# если хочешь reply-кнопку в меню — добавишь "Поддержка"
@support_router.message(Command(SUPPORT))
async def support_start(message: Message, state: FSMContext, support_service: SupportService, user) -> None:
    """Старт поддержки через команду /support."""
    await start_support_flow(message, state, support_service, user)

@support_router.callback_query(F.data == SUPPORT_START)
async def support_start_callback(callback: CallbackQuery, state: FSMContext, support_service: SupportService, user) -> None:
    """Старт поддержки через кнопку."""
    await callback.answer()

    await start_support_flow(callback, state, support_service, user)

# Вопрос клиента по любому товару
@support_router.callback_query(F.data.startswith(MESSAGE_OWNER_CB))
async def support_start_item_callback(
    callback: CallbackQuery,
    state: FSMContext,
    support_service: SupportService,
    item_service: ItemService,
    user,
) -> None:
    """Старт поддержки из карточки товара с привязкой обращения к item_id."""
    await callback.answer()

    raw_item_id = (callback.data or "").removeprefix(MESSAGE_OWNER_CB)
    try:
        item_id = int(raw_item_id)
    except ValueError:
        await callback.answer("Некорректный товар.", show_alert=True)
        return

    try:
        item = await item_service.get_public_item_by_id(item_id)
    except ServiceError:
        await callback.answer("Ошибка. Попробуйте позже.", show_alert=True)
        return

    if item is None:
        await callback.answer("Товар не найден или сейчас недоступен.", show_alert=True)
        return

    await start_support_flow(callback, state, support_service, user, item_id=item.id, item_title=item.title)

# Вопрос клиента внутри его аренды
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


@support_router.callback_query(F.data.startswith(SUPPORT_CONTINUE))
async def support_continue_open_ticket(callback: CallbackQuery, state: FSMContext, support_service: SupportService, user) -> None:
    """Позволить клиенту добавить сообщение в уже открытый тикет."""

    raw_ticket_id = (callback.data or "").removeprefix(SUPPORT_CONTINUE)
    try:
        ticket_id = int(raw_ticket_id)
    except ValueError:
        await callback.answer("Некорректный тикет.", show_alert=True)
        return

    ticket = await support_service.get_ticket_by_id(ticket_id)
    if ticket is None or ticket.user_id != user.id:
        await callback.answer("Тикет не найден.", show_alert=True)
        return

    if ticket.status.value != "open":
        await callback.answer("Этот тикет уже закрыт.", show_alert=True)
        return

    await callback.answer()

    await state.set_state(SupportStates.waiting_text)
    await state.update_data(support_existing_ticket_id=ticket_id, support_rental_id=None, support_item_id=None)
    await send_or_edit(
        callback,
        f"✉️ <b>Ответ в тикет #{ticket_id}</b>\n\nНапишите сообщение для поддержки.",
        build_support_cancel_keyboard(),
    )

# ──────────────────────────────────────────────── FSM-поддержки ───────────────────────────────────────────────────────
# обрабатывает оба варианта "вопроса клиента"
async def start_support_flow(
        event: Message | CallbackQuery,
        state: FSMContext,
        support_service: SupportService,
        user,
        *,
        rental_id: int | None = None,
        item_id: int | None = None,
        item_title: str | None = None
) -> None:
    """Единый вход в поддержку"""

    if rental_id is not None:
        ticket_kind = "rentals"
    elif item_id is not None:
        ticket_kind = "items"
    else:
        ticket_kind = "general"

    open_ticket = await support_service.get_open_ticket_by_user(user.id, kind=ticket_kind)
    if open_ticket:
        await send_or_edit(
            event,
            build_support_already_open_text(open_ticket.id, kind=ticket_kind),
            build_support_continue_keyboard(open_ticket.id)
        )
        return

    await state.set_state(SupportStates.waiting_text)
    await state.update_data(
        support_rental_id=rental_id,
        support_item_id=item_id
    ) # ???

    await send_or_edit(event, build_support_request_text(item_title), build_support_cancel_keyboard()) # None


@support_router.message(SupportStates.waiting_text, F.text)
async def receive_support_text(
    message: Message,
    state: FSMContext,
    support_service: SupportService,
    user,
    admin_ids: list[int],
    notification_service: NotificationService,
) -> None:
    """Обрабатывает сообщение пользователя для службы поддержки. Создание тикета и отправка уведомления админам."""

    text = (message.text or "").strip()
    if not text:
        await send_or_edit(message, "❌ Текст не может быть пустым. Пожалуйста, отправьте текст обращения.")
        return

    data = await state.get_data()
    rental_id = data.get("support_rental_id")
    item_id = data.get("support_item_id")
    existing_ticket_id = data.get("support_existing_ticket_id")

    if existing_ticket_id:
        ticket = await support_service.append_user_reply(ticket_id=int(existing_ticket_id), user_id=user.id,
                                                         reply_text=text)
        await state.clear()

        if ticket is None:
            await send_or_edit(message, "⚠️ Тикет не найден или уже закрыт. Создайте новое обращение через поддержку.")
            return

        await send_or_edit(message, f"✅ Ваш ответ добавлен в тикет #{ticket.id}. Поддержка увидит сообщение.")
        await notification_service.notify_admins_support_user_reply(admin_ids, ticket, user, text,
                                        reply_markup=get_admin_support_ticket_notification_keyboard(ticket.id))
        return

    if item_id:
        subject = f"Вопрос по товару #{item_id}"
    elif rental_id:
        subject = f"Заявка на аренду #{rental_id}"
    else:
        subject = None

    try:
        internal = SupportTicketCreateInternal(
                user_id=user.id,
                #telegram_id=int(user.telegram_id),
                #username=user.username,
                text=text,
                subject=subject,
                item_id=item_id,
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
    await notification_service.notify_user_support_ticket_created(user.telegram_id, ticket)
    # await send_or_edit(message, build_support_confirmation_text())

    # отправляем сообщение поддержки админу
    await notification_service.notify_admins_new_support_ticket(
        admin_ids,
        ticket,
        user,
        reply_markup=get_admin_support_ticket_notification_keyboard(ticket.id),
    )

    # Возвращаем пользователя в главное меню
    # await show_main_menu(message, user)


# ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
@support_router.callback_query(F.data == SUPPORT_CANCEL)
async def cancel_support(callback: CallbackQuery, state: FSMContext, user) -> None:
    """Отменить обращение в поддержку."""
    await callback.answer()

    await state.clear()
    await callback.message.answer("❌ Обращение в поддержку отменено.")

    # Возвращаем пользователя в главное меню
    await show_main_menu(callback, user)