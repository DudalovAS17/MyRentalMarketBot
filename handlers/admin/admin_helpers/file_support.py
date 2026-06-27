from aiogram.types import CallbackQuery, Message

from services.admin_service import AdminActionService
from schemas.support import SupportTicketOut
from schemas.user import UserOut
from services.support_service import SupportService
from status.support_ticket_status import SupportTicketStatus
from utils.functions import send_or_edit

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
    ticket_user: UserOut,
    ticket: SupportTicketOut,
    reply_text: str,
) -> None:
    """Отправить ответ пользователю и записать audit log"""

    # Отправляем ответ пользователю
    await message.bot.send_message(
        chat_id=ticket_user.telegram_id,
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
            "to_user_id": ticket_user.id,
            "to_telegram_id": int(ticket_user.telegram_id),
        },
    )


async def notify_ticket_closed_and_audit(
    callback: CallbackQuery,
    admin_service: AdminActionService,
    ticket_user: UserOut,
    ticket: SupportTicketOut,
    admin_tg_id: int,
) -> None:
    """Уведомить пользователя о закрытии тикета и записать audit log."""

    # Уведомляем пользователя
    await callback.bot.send_message(
        chat_id=int(ticket_user.telegram_id),
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
        payload={"to_user_id": ticket.id, "to_telegram_id": int(ticket_user.telegram_id)},
    )