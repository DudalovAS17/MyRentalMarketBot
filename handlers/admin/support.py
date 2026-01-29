from __future__ import annotations

import logging
from datetime import datetime

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from db.models.support_ticket import SupportTicketStatus
from keyboards.admin_kb import (
    get_admin_support_list_keyboard,
    get_admin_support_ticket_keyboard,
)
from services.admin_service import AdminActionService
from services.support_service import SupportService
from states.support_ticket import AdminSupportStates
from utils.functions import send_or_edit

logger = logging.getLogger(__name__)

admin_support_router = Router()


def _format_datetime(dt: datetime | None) -> str:
    if not dt:
        return "—"
    return dt.strftime("%d.%m.%Y %H:%M")


def _render_ticket_card(ticket, user) -> str:
    username = f"@{user.username}" if user and user.username else "—"
    created_at = _format_datetime(getattr(ticket, "created_at", None))
    status_value = ticket.status.value if hasattr(ticket.status, "value") else str(ticket.status)
    return (
        "🎫 <b>Тикет поддержки</b>\n\n"
        f"ID: <b>#{ticket.id}</b>\n"
        f"Статус: <b>{status_value.upper()}</b>\n"
        f"Дата: {created_at}\n\n"
        f"👤 <b>Пользователь:</b> {user.display_name if user else '—'}\n"
        f"🆔 <b>Telegram ID:</b> <code>{user.telegram_id if user else '—'}</code>\n"
        f"💬 <b>Username:</b> {username}\n\n"
        f"📝 <b>Текст:</b>\n{ticket.text}"
    )


@admin_support_router.callback_query(F.data == "admin:support")
async def admin_support_list(callback: CallbackQuery, support_service: SupportService, user) -> None:
    await callback.answer()
    await _show_support_list(callback, support_service, page=1)


@admin_support_router.callback_query(F.data.startswith("admin:support:page:"))
async def admin_support_list_page(callback: CallbackQuery, support_service: SupportService, user) -> None:
    await callback.answer()
    page = int(callback.data.split(":")[-1])
    await _show_support_list(callback, support_service, page=page)


async def _show_support_list(event: CallbackQuery, support_service: SupportService, page: int) -> None:
    rows, has_next = await support_service.list_open_tickets(page)
    if not rows:
        await send_or_edit(
            event,
            "🆘 <b>Открытые тикеты</b>\n\nОткрытых тикетов пока нет.",
            markup=get_admin_support_list_keyboard([], page=1, has_next=False),
        )
        return

    lines = []
    for row in rows:
        ticket = row["ticket"]
        user = row["user"]
        created_at = _format_datetime(getattr(ticket, "created_at", None))
        lines.append(
            f"🎫 #{ticket.id} — {user.display_name if user else '—'} ({created_at})"
        )

    text = "🆘 <b>Открытые тикеты</b>\n\n" + "\n".join(lines)
    await send_or_edit(
        event,
        text,
        markup=get_admin_support_list_keyboard(rows, page=page, has_next=has_next),
    )


@admin_support_router.callback_query(F.data.startswith("admin:support:view:"))
async def admin_support_view(callback: CallbackQuery, support_service: SupportService, user) -> None:
    await callback.answer()
    ticket_id = int(callback.data.split(":")[-1])
    details = await support_service.get_details(ticket_id)
    if not details:
        return await send_or_edit(callback, f"❌ Тикет #{ticket_id} не найден.", None)

    ticket = details["ticket"]
    ticket_user = details["user"]
    text = _render_ticket_card(ticket, ticket_user)
    status_value = ticket.status.value if hasattr(ticket.status, "value") else str(ticket.status)
    await send_or_edit(
        callback,
        text,
        markup=get_admin_support_ticket_keyboard(ticket.id, status_value),
    )


@admin_support_router.callback_query(F.data.startswith("admin:support:reply:"))
async def admin_support_reply_prompt(callback: CallbackQuery, state: FSMContext, support_service: SupportService, user):
    await callback.answer()
    ticket_id = int(callback.data.split(":")[-1])
    details = await support_service.get_details(ticket_id)
    if not details:
        return await send_or_edit(callback, f"❌ Тикет #{ticket_id} не найден.", None)

    ticket = details["ticket"]
    if ticket.status != SupportTicketStatus.OPEN:
        return await send_or_edit(callback, f"⚠️ Тикет #{ticket_id} уже закрыт.", None)

    await state.set_state(AdminSupportStates.waiting_reply_text)
    await state.update_data(ticket_id=ticket_id)
    await send_or_edit(callback, f"✉️ Введите ответ для тикета #{ticket_id}:", None)


@admin_support_router.message(AdminSupportStates.waiting_reply_text, F.text)
async def admin_support_reply_send(
    message: Message,
    state: FSMContext,
    support_service: SupportService,
    admin_service: AdminActionService,
    user,
):
    data = await state.get_data()
    ticket_id = data.get("ticket_id")
    if not ticket_id:
        await state.clear()
        return await send_or_edit(message, "⚠️ Не удалось определить тикет. Попробуйте снова.")

    details = await support_service.get_details(int(ticket_id))
    if not details:
        await state.clear()
        return await send_or_edit(message, f"❌ Тикет #{ticket_id} не найден.")

    ticket = details["ticket"]
    ticket_user = details["user"]
    if ticket.status != SupportTicketStatus.OPEN:
        await state.clear()
        return await send_or_edit(message, f"⚠️ Тикет #{ticket_id} уже закрыт.")

    reply_text = (message.text or "").strip()
    if not reply_text:
        return await send_or_edit(message, "Пожалуйста, введите текст ответа.")

    await message.bot.send_message(
        chat_id=int(ticket_user.telegram_id),
        text=(
            f"💬 <b>Ответ поддержки</b> по тикету #{ticket.id}:\n\n"
            f"{reply_text}"
        ),
        parse_mode="HTML",
    )

    await admin_service.log_action(
        admin_id=int(user.telegram_id),
        action_type="SUPPORT_REPLY",
        entity_type="support_ticket",
        entity_id=ticket.id,
        payload={
            "text": reply_text,
            "to_telegram_id": int(ticket_user.telegram_id),
        },
    )

    await state.clear()
    await send_or_edit(message, f"✅ Ответ отправлен пользователю. Тикет #{ticket.id}.")


@admin_support_router.callback_query(F.data.startswith("admin:support:close:"))
async def admin_support_close(
    callback: CallbackQuery,
    support_service: SupportService,
    admin_service: AdminActionService,
    user,
):
    await callback.answer()
    ticket_id = int(callback.data.split(":")[-1])
    details = await support_service.get_details(ticket_id)
    if not details:
        return await send_or_edit(callback, f"❌ Тикет #{ticket_id} не найден.", None)

    ticket = details["ticket"]
    ticket_user = details["user"]
    if ticket.status != SupportTicketStatus.OPEN:
        return await send_or_edit(callback, f"⚠️ Тикет #{ticket_id} уже закрыт.", None)

    closed = await support_service.close_ticket(ticket_id)
    if not closed:
        return await send_or_edit(callback, f"⚠️ Не удалось закрыть тикет #{ticket_id}.", None)

    await callback.bot.send_message(
        chat_id=int(ticket_user.telegram_id),
        text=(
            f"✅ Ваш тикет поддержки #{ticket.id} закрыт. "
            "Если у вас остались вопросы, вы можете создать новый тикет командой /support."
        ),
        parse_mode="HTML",
    )

    await admin_service.log_action(
        admin_id=int(user.telegram_id),
        action_type="SUPPORT_CLOSE",
        entity_type="support_ticket",
        entity_id=ticket.id,
        payload={"to_telegram_id": int(ticket_user.telegram_id)},
    )

    updated_details = await support_service.get_details(ticket_id)
    updated_ticket = updated_details["ticket"] if updated_details else ticket
    updated_user = updated_details["user"] if updated_details else ticket_user
    text = _render_ticket_card(updated_ticket, updated_user)
    status_value = updated_ticket.status.value if hasattr(updated_ticket.status, "value") else str(updated_ticket.status)
    await send_or_edit(
        callback,
        text,
        markup=get_admin_support_ticket_keyboard(updated_ticket.id, status_value),
    )
