from aiogram.types import CallbackQuery, Message

from services.admin_service import AdminActionService
from services.notif_service import NotificationService
from services.support_service import SupportService

from schemas.support import SupportTicketOut
from schemas.user import UserOut
from utils.functions import send_or_edit


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

    if not support_service.is_open_ticket(ticket):
        await send_or_edit(event, f"⚠️ Тикет #{ticket_id} уже закрыт.", None)
        return None

    return ticket


async def send_support_reply_and_audit(
    message: Message,
    admin_service: AdminActionService,
    notification_service: NotificationService,
    ticket_user: UserOut,
    ticket: SupportTicketOut,
    reply_text: str,
) -> bool:
    """Безопасно отправить ответ клиенту и записать audit log"""

    # Отправляем ответ клиенту
    delivered = await notification_service.notify_user_support_reply(ticket_user.telegram_id, ticket, reply_text)

    # Audit log
    await admin_service.log_action(
        admin_tg_id=int(message.from_user.id),
        #admin_id=ticket_user.id,
        action_type="SUPPORT_REPLY",
        entity_type="support_ticket",
        entity_id=ticket.id,
        payload={
            "text": reply_text,
            "user_id": ticket_user.id,
            "tg_id": int(ticket_user.telegram_id),
            "notification_delivery": "sent" if delivered else "failed",
        },
    )

    return delivered


async def notify_ticket_closed_and_audit(
    callback: CallbackQuery,
    admin_service: AdminActionService,
    notification_service: NotificationService,
    ticket_user: UserOut,
    ticket: SupportTicketOut,
    admin_tg_id: int,
) -> bool:
    """Безопасно уведомить пользователя о закрытии тикета и записать audit log."""

    # Уведомляем клиента
    delivered = await notification_service.notify_user_support_ticket_closed(ticket_user.telegram_id, ticket)

    # Audit log
    await admin_service.log_action(
        admin_tg_id=admin_tg_id,
        action_type="SUPPORT_CLOSE",
        entity_type="support_ticket",
        entity_id=ticket.id,
        payload={
            "user_id": ticket_user.id,
            "telegram_id": int(ticket_user.telegram_id),
            "notification_delivery": "sent" if delivered else "failed",
        },
    )

    return delivered