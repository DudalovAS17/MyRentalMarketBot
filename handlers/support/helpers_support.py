from datetime import datetime
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from schemas.support import SupportTicketOut
from schemas.user import UserOut

# render_admin_ticket_message - Сформировать уведомление админам о новом тикете
#

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
    rental_line = f"📄 <b>Заявка:</b> #{ticket.rental_id}\n" if ticket.rental_id else ""
    return (
        f"🆘 🎫 <b>Новый тикет поддержки </b> #{ticket.id}\n\n"
        f"👤 <b>Пользователь:</b> {username_text} (🆔 id={user.id}) \n"
        f"{rental_line}"
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