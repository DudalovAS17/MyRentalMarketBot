import logging
from datetime import datetime
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.exceptions import TelegramAPIError

from schemas.support import SupportTicketOut
from schemas.user import UserOut
from keyboards.admin_kb import get_admin_support_ticket_notification_keyboard

logger = logging.getLogger(__name__)

# ──────────────────────────────────────── Format ──────────────────────────────────────────────────────────────────────
def format_datetime(dt: datetime | None) -> str:
    """Сформатировать дату для UI поддержки."""
    if not dt:
        return "—"
    return dt.strftime("%d.%m.%Y %H:%M")

# ─────────────────────────────────────────── Text ─────────────────────────────────────────────────────────────────────
def render_admin_ticket_message(ticket: SupportTicketOut, user: UserOut) -> str:
    """Сформировать уведомление админам о новом тикете."""
    username_text = f"@{user.username}" if user.username else "—"
    created = format_datetime(ticket.created_at)

    return (
        f"🆘 🎫 <b>Новый тикет поддержки </b> #{ticket.id}\n\n"
        f"👤 <b>Пользователь:</b> @{username_text} (🆔 id={user.id}) \n"
        #f"🆔 <b>Telegram ID:</b> <code>{user.telegram_id if user else '—'}</code>\n"
        f"📅 <b>Создан:</b> {created}\n"
        f"📝 <b>Текст:</b>\n{ticket.text}"
    )

def build_support_request_text() -> str:
    """Сформировать prompt обращения в поддержку."""
    return (
        "📞 <b>Поддержка</b>\n\n"
        "Опишите вашу проблему или вопрос как можно подробнее.\n"
        "Мы постараемся помочь как можно скорее."
    )

def build_support_confirmation_text() -> str:
    """Сформировать подтверждение создания обращения."""
    return (
        "✅ <b>Спасибо за ваше обращение!</b>\n\n"
        "Ваше сообщение получено и будет рассмотрено нашей службой поддержки в ближайшее время.\n\n"
        "Мы свяжемся с вами, если потребуется дополнительная информация."
    )

def build_support_already_open_text(ticket_id: int) -> str:
    """Сформировать текст ошибки уже открытого тикета."""
    return (
        f"⚠️ У вас уже есть открытое обращение (тикет #{ticket_id}).\n"
        "Дождитесь ответа поддержки или создайте новое после закрытия."
    )

def build_support_already_open_after_create_text(ticket_id: int) -> str:
    """Сформировать текст ошибки повторного создания тикета."""
    return (
        f"⚠️ У вас уже есть открытый тикет #{ticket_id}. "
        "Дождитесь ответа поддержки."
    )

# ─────────────────────────────────────────────── Keyboard ─────────────────────────────────────────────────────────────
def build_support_cancel_keyboard() -> InlineKeyboardMarkup:
    """Собрать клавиатуру отмены обращения в поддержку."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="support:cancel")] # "cancel_support"
        ]
    )

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