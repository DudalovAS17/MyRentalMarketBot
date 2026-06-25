from datetime import datetime
from aiogram.types import CallbackQuery, Message

from services.admin_service import AdminActionService
from .keyboard import get_admin_support_list_keyboard, get_admin_support_ticket_keyboard
from schemas.support import SupportTicketOut
from services.support_service import SupportService
from status.support_ticket_status import SupportTicketStatus
from utils.functions import send_or_edit

# ────────────────────────────────────────────────── parse ─────────────────────────────────────────────────────────────
def parse_support_page(raw: str | None, *, default: int = 1) -> int:
    """Распарсить номер страницы из callback data поддержки"""
    try:
        page = int((raw or "").split(":")[-1])
    except (ValueError, IndexError):
        return default
    return max(1, page)

def parse_support_ticket_id(raw: str | None) -> int | None:
    """Распарсить ticket_id из callback data поддержки"""
    try:
        return int((raw or "").split(":")[-1])
    except (ValueError, IndexError):
        return None

# ────────────────────────────────────────────────── texts ─────────────────────────────────────────────────────────────
def format_datetime(dt: datetime | None) -> str: # ("%d.%m %H:%M")
    """Сформатировать дату для админского UI"""
    if not dt:
        return "—"
    return dt.strftime("%d.%m.%Y %H:%M")

def format_ticket_card(ticket: SupportTicketOut) -> str:
    """Сформировать текст карточки тикета поддержки"""
    username = ticket.username or "—"
    created = format_datetime(ticket.created_at)
    status = ticket.status.value
    return (
        f"🆘 🎫 <b>Тикет поддержки</b> #{ticket.id}\n\n"
        f"💬 <b>Username:</b> {username}\n\n"
        f"Статус: <b>{status}</b>\n"
        f"👤 <b>Пользователь:</b> @{username} (🆔 tg_id={ticket.telegram_id})\n"
        f"📅 <b>Создан:</b> 🕒 {created}\n\n"
        f"📝 <b>Текст:</b>\n{ticket.text}"
    )

# ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────


async def show_support_ticket_list(event: Message | CallbackQuery, support_service: SupportService,page: int) -> None:
    """Показать список открытых тикетов поддержки"""

    tickets, has_next = await support_service.list_open_tickets(page)
    lines = [f"📭 <b>Открытые тикеты</b> (стр. {page})\n"]

    if not tickets:
        lines.append("Пока нет открытых тикетов.")
    else:
        for ticket in tickets:
            created_at = format_datetime(ticket.created_at)
            uname = f"@{ticket.username}" if ticket.username else f"tg_id={ticket.telegram_id}"
            lines.append(f"•🎫• <b>#{ticket.id}</b> — {uname} — {created_at}")

    rows = [{"ticket": ticket} for ticket in tickets]
    await send_or_edit(
        event,
        "\n".join(lines),
        get_admin_support_list_keyboard(rows, page=page, has_next=has_next),
    )

async def show_support_ticket_card_or_not_found(
    event: Message | CallbackQuery,
    support_service: SupportService,
    ticket_id: int,
) -> None: #SupportTicketOut | None:
    """Показать карточку тикета или not-found сообщение"""

    ticket = await support_service.get_ticket_by_id(ticket_id)
    if not ticket:
        await send_or_edit(event, f"❌ Тикет #{ticket_id} не найден.", None)
        return #None

    await send_or_edit(
        event,
        format_ticket_card(ticket),
        get_admin_support_ticket_keyboard(ticket.id, ticket.status),
    )

    #return ticket


def is_open_ticket(ticket: SupportTicketOut) -> bool:
    """Проверить, что тикет открыт"""
    return ticket.status == SupportTicketStatus.OPEN


async def load_open_support_ticket_or_notify(
    event: Message | CallbackQuery,
    support_service: SupportService,
    ticket_id: int,
) -> SupportTicketOut | None:
    """Загрузить открытый тикет или показать UX-ошибку"""

    ticket = await support_service.get_ticket_by_id(ticket_id)

    if not ticket:
        await send_or_edit(event, f"❌ Тикет #{ticket_id} не найден.", None)
        return None

    if not is_open_ticket(ticket):
        await send_or_edit(event, f"⚠️ Тикет #{ticket_id} уже закрыт.", None)
        return None

    return ticket


async def send_support_reply_and_audit(
    message: Message,
    admin_service: AdminActionService,
    ticket: SupportTicketOut,
    reply_text: str,
) -> None:
    """Отправить ответ пользователю и записать audit log"""

    # Отправляем ответ пользователю
    await message.bot.send_message(
        chat_id=int(ticket.telegram_id),
        text=f"💬 <b>Ответ поддержки</b> по тикету #{ticket.id}:\n\n{reply_text}",
        parse_mode="HTML",
    )

    # Audit log
    await admin_service.log_action(
        admin_tg_id=int(message.from_user.id),
        action_type="SUPPORT_REPLY",
        entity_type="support_ticket",
        entity_id=ticket.id,
        payload={
            "text": reply_text,
            "to_telegram_id": int(ticket.telegram_id),
        },
    )


async def notify_ticket_closed_and_audit(
    callback: CallbackQuery,
    admin_service: AdminActionService,
    ticket: SupportTicketOut,
    admin_tg_id: int,
) -> None:
    """Уведомить пользователя о закрытии тикета и записать audit log."""

    # Уведомляем пользователя
    await callback.bot.send_message(
        chat_id=int(ticket.telegram_id),
        text=(
            f"✅ Ваш тикет поддержки #{ticket.id} закрыт. "
            "Если у вас остались вопросы, вы можете создать новый тикет командой /support."
        ),
        parse_mode="HTML",
    )

    # Audit log
    await admin_service.log_action(
        admin_tg_id=admin_tg_id,
        action_type="SUPPORT_CLOSE",
        entity_type="support_ticket",
        entity_id=ticket.id,
        payload={"to_telegram_id": int(ticket.telegram_id)},
    )