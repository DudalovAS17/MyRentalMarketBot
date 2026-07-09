from datetime import datetime

from schemas.support import SupportMessageOut, SupportTicketOut
from schemas.rental import RentalAdminDetailsOut
from schemas.user import UserOut
from utils.validators import format_price
from status.user_status import AccountStatus
from status.rental_status import STATUS_LABELS

def _truncate(text: str, max_len: int = 48) -> str:
    """Аккуратно укоротить длинный текст для списка заявок."""
    normalized = " ".join((text or "—").split())
    if len(normalized) <= max_len:
        return normalized
    return f"{normalized[:max_len - 1].rstrip()}…"

# ──────────────────────────────────────────────────   ─────────────────────────────────────────────────────────────
def format_user_line(label: str, user) -> str:
    """Сформировать строку пользователя для карточки заявки"""
    if not user:
        return f"{label}: <i>не найден</i>"
    tg = user.telegram_id
    username = user.username
    return f"{label}: id={user.id}, tg={tg}, @{username}"

def format_deal_list_item(details: RentalAdminDetailsOut) -> str:
    """Сформировать компактную строку заявки для списка в админке."""
    r = details.rental
    item = details.item
    status_label = STATUS_LABELS.get(r.status, r.status.value)
    title = _truncate(item.title or f"Товар #{r.item_id}")
    created = format_datetime(r.created_at)
    client_name = _truncate(r.client_name or getattr(details.user, "full_name", None) or "клиент не указан", 28)

    return (
        f"<b>#{r.id}</b> · <b>{status_label}</b>\n"
        f"📦 {title}\n"
        f"👤 {client_name} · {r.quantity} шт. · {created}"
    )


def format_deal_details(details: RentalAdminDetailsOut) -> str:
    """Сформировать текст карточки заявки для админки"""
    r = details.rental
    item = details.item
    client = details.user

    item_title = item.title or f"Товар #{r.item_id}"
    status_val = STATUS_LABELS.get(r.status, r.status.value)

    delivery = "нужна" if r.delivery_needed else "не нужна"
    address_line = f"• Адрес доставки: {r.delivery_address or '—'}\n" if r.delivery_needed else ""
    username = f"@{client.username}" if client and client.username else "—"

    created = format_datetime(r.created_at)

    return (
        f"🧾 <b>Заявка #{r.id}</b>\n\n"
        f"• Статус: <b>{status_val}</b>\n"
        f"• Товар: <b>{item_title}</b>\n"
        f"• Количество: <b>{r.quantity}</b>\n"
        f"• Период: {r.rental_period_text or '—'}\n"
        f"• Доставка: {delivery}\n"
        f"{address_line}"
        f"• Расчётная стоимость: {r.total_price or '—'}\n"
        f"• Финальная стоимость: {r.final_price or '—'}\n\n"
        f"👤 Клиент: {r.client_name or '—'}\n"
        f"Telegram: {username} / tg_id={getattr(client, 'telegram_id', '—')}\n"
        f"☎️ Телефон: {r.client_phone or '—'}\n"
        f"💬 Комментарий клиента: {r.client_comment or '—'}\n"
        f"📝 Комментарий менеджера: {r.manager_comment or '—'}\n"
        f"📅 Создана: {created}\n"
    )

# подчисть
def format_deal_contact(details: RentalAdminDetailsOut) -> str:
    """Сформировать контактную карточку клиента по заявке."""
    r = details.rental
    client = details.user
    username = client.username if client and client.username else None
    username_line = f"@{username}" if username else "—"
    link_line = f"https://t.me/{username}" if username else "—"

    return (
        f"📞 <b>Контакт клиента по заявке #{r.id}</b>\n\n"
        f"• Имя из заявки: <b>{r.client_name or '—'}</b>\n"
        f"• Имя профиля: <b>{getattr(client, 'full_name', None) or '—'}</b>\n"
        f"• Телефон из заявки: <b>{r.client_phone or '—'}</b>\n"
        f"• Телефон профиля: <b>{getattr(client, 'phone', None) or '—'}</b>\n"
        f"• Username: {username_line}\n"
        f"• Telegram ID: <code>{getattr(client, 'telegram_id', '—')}</code>\n"
        f"• Ссылка: {link_line}\n"
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

def format_support_message_history(messages: list[SupportMessageOut] | None, *, max_messages: int = 10) -> str:
    """Сформировать компактную историю переписки по тикету для админской карточки."""
    if not messages:
        return "🧵 <b>История:</b> —"

    visible_messages = messages[-max_messages:]
    hidden_count = max(0, len(messages) - len(visible_messages))
    lines = ["🧵 <b>История:</b>"]
    if hidden_count:
        lines.append(f"… скрыто старых сообщений: {hidden_count}")

    label_by_sender = {
        "user": "👤 Клиент",
        "admin": "👨‍💼 Админ",
        "system": "⚙️ Система",
    }
    for message in visible_messages:
        label = label_by_sender.get(message.sender_type.value, "💬 Сообщение")
        created = format_datetime(message.created_at)
        lines.append(f"{label} · {created}:\n{message.text}")

    return "\n\n".join(lines)

# обдумай
def format_ticket_card(ticket: SupportTicketOut, user: UserOut = None, messages: list[SupportMessageOut] | None = None) -> str:
    """Сформировать текст карточки тикета поддержки"""
    user_line = f"🆔 = {ticket.user_id}" if ticket.user_id else f"tg_id={user.telegram_id}" # @{user.username}
    subject_line = f"📌 <b>Тема:</b> {ticket.subject}\n" if ticket.subject else ""
    item_line = f"📦 <b>Товар:</b> #{ticket.item_id}\n" if ticket.item_id else ""
    rental_line = f"📄 <b>Заявка:</b> #{ticket.rental_id}\n" if ticket.rental_id else ""
    created = format_datetime(ticket.created_at)
    status = ticket.status.value

    phone = getattr(user, "phone", None) if user else None
    username = f"@{user.username}" if user and user.username else "—"
    contact_line = f"☎️ <b>Телефон:</b> {phone or '—'}\n💬 <b>Username:</b> {username}\n"

    history_text = format_support_message_history(messages)

    return (f"🆘 🎫 <b>Тикет поддержки</b> #{ticket.id}\n\n"

        f"Статус: <b>{status}</b>\n"
        f"👤 <b>Пользователь:</b> {user_line}\n"
        f"{contact_line}"
        f"{subject_line}"
        f"{item_line}"
        f"{rental_line}"
        f"📅 <b>Создан:</b> 🕒 {created}\n\n"
        #f"📝 <b>Текст:</b>\n{ticket.text}"
        f"{history_text}"
    )

# ──────────────────────────────────────────────────  ─────────────────────────────────────────────────────────────
