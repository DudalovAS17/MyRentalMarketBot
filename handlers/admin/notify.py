import logging
from aiogram.exceptions import TelegramAPIError

from admin_helpers.keyboard import get_admin_support_ticket_notification_keyboard

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
async def notify_admins(bot, admin_ids: list[int], notification_text: str, ticket_id: int) -> None:
    """Уведомить админов о новом тикете."""
    if not admin_ids:
        return

    kb = get_admin_support_ticket_notification_keyboard(ticket_id)

    for admin_id in admin_ids:
        try:
            await bot.send_message(chat_id=admin_id, text=notification_text, reply_markup=kb, parse_mode="HTML")
        except TelegramAPIError as exc:
            logger.warning("Не удалось уведомить админа %s о тикете %s: %s", admin_id, ticket_id, exc)
            continue