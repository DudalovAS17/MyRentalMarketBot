from datetime import datetime
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# ──────────────────────────────────────── Format ──────────────────────────────────────────────────────────────────────
def format_datetime(dt: datetime | None) -> str:
    """Сформатировать дату для UI поддержки."""
    if not dt:
        return "—"
    return dt.strftime("%d.%m.%Y %H:%M")

# ─────────────────────────────────────────── Text ─────────────────────────────────────────────────────────────────────
def build_support_request_text(item_title: str | None = None) -> str:
    """Сформировать prompt обращения в поддержку."""
    context = f"Вопрос по товару: <b>{item_title}</b>\n\n" if item_title else ""
    return (
        "📞 <b>Поддержка</b>\n\n"
        f"{context}"
        "Опишите вашу проблему или вопрос как можно подробнее.\n"
        "Мы постараемся помочь как можно скорее."
    )

def support_kind_name(kind: str | None) -> str:
    """Клиентское название контура поддержки."""
    if kind == "items":
        return "по товару"
    if kind == "rentals":
        return "по аренде"
    return "в поддержке"

def build_support_already_open_text(ticket_id: int, *, kind: str | None = None) -> str:
    """Сформировать текст ошибки уже открытого тикета."""
    return (
        f"⚠️ У вас уже есть открытое обращение {support_kind_name(kind)}.\n"
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