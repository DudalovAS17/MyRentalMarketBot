from datetime import datetime

from schemas.support import SupportTicketOut
from schemas.rental import RentalAdminDetailsOut
from utils.functions import format_price
from status.user_status import AccountStatus

# ──────────────────────────────────────────────────   ─────────────────────────────────────────────────────────────
def format_user_line(label: str, user) -> str:
    """Сформировать строку пользователя для карточки заявки"""
    if not user:
        return f"{label}: <i>не найден</i>"
    tg = user.telegram_id
    username = user.username
    return f"{label}: id={user.id}, tg={tg}, @{username}"

def format_deal_details(details: RentalAdminDetailsOut) -> str:
    """Сформировать текст карточки заявки для админки"""
    r = details.rental
    item = details.item
    client = details.user

    item_title = item.title or f"item_id={r.item_id}"
    status_val = r.status.value

    return (
        f"🧾 <b>Заявка #{r.id}</b>\n\n"
        f"• Статус: <b>{status_val}</b>\n"
        f"• Товар: <b>{item_title}</b>\n"
        f"• Период: {r.rental_period_text or '—'}\n"
        f"• Расчётная стоимость: {r.total_price or '—'}\n"
        f"• Финальная стоимость: {r.final_price or '—'}\n\n"
        f"{format_user_line('👤 Клиент', client)}\n"
        f"☎️ Телефон: {r.client_phone or '—'}\n"
        f"💬 Комментарий клиента: {r.client_comment or '—'}\n"
        f"📝 Комментарий менеджера: {r.manager_comment or '—'}\n"
    )

# ────────────────────────────────────────────────── items moderation ──────────────────────────────────────────────────
# карточка объявления
def format_item_details(item) -> str:
    """Сформировать текст карточки товара для админки."""
    price_text = format_price(item.price) if item.price is not None else "—"
    quantity = getattr(item, "available_quantity", None)

    return (
        f"📦 <b>Товар #{item.id}</b>\n\n"
        f"• Статус: <b>{item.status.value}</b>\n"
        #f"• Владелец: <b>{item.user_id}</b>\n"
        f"• Название: <b>{item.title}</b>\n"
        f"• Цена: <b>{price_text} ₽/день</b>\n"
        f"• Доступное количество: <b>{quantity if quantity is not None else '—'}</b>\n"
        f"• Описание: {item.description or '—'}\n"
    )

# ────────────────────────────────────────────────── users ─────────────────────────────────────────────────────────────
def format_user_card(user) -> str:
    """Сформировать карточку пользователя для админки"""
    username = user.username
    status = user.account_status

    lines = [
        "👥 <b>Пользователь</b>",
        f"• id-клиента: <b>{user.id}</b>",
        f"• Имя клиента: @{username}" if username else "• username: —",
        f"• Статус аккаунта: <b>{status.value}</b>",
    ]

    if status == AccountStatus.BANNED:
        banned_at = user.banned_at
        banned_by_admin_id = user.banned_by_admin_id
        ban_reason = user.ban_reason

        if banned_at:
            lines.append(f"• banned_at: {banned_at}")
        if banned_by_admin_id:
            lines.append(f"• banned_by_admin_id: {banned_by_admin_id}")
        if ban_reason:
            lines.append(f"• ban_reason: {ban_reason}")

    return "\n".join(lines)

# ────────────────────────────────────────────────── support ─────────────────────────────────────────────────────────────
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

# ──────────────────────────────────────────────────  ─────────────────────────────────────────────────────────────
