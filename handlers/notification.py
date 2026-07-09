from datetime import datetime
from html import escape

from schemas.rental import RentalAdminDetailsOut, RentalDetailsOut
from schemas.support import SupportTicketOut
from schemas.user import UserOut
from status.rental_status import RentalStatus, STATUS_LABELS


def safe(value: object | None, default: str = "—") -> str:
    """Преобразовать значение в строку для Telegram-сообщения."""
    if value is None:
        return default
    text = str(value).strip()
    return escape(text) if text else default

def format_datetime(dt: datetime | None) -> str:
    """Сформатировать дату для уведомления."""
    if not dt:
        return "—"
    return escape(dt.strftime("%d.%m.%Y %H:%M"))

def rental_id(details: RentalDetailsOut | RentalAdminDetailsOut) -> int:
    """Вернуть ID заявки из клиентского или админского details DTO."""
    return details.rental.id

def support_context(ticket: SupportTicketOut) -> str:
    """Вернуть человекочитаемый контекст тикета поддержки."""
    if ticket.rental_id:
        return f"Аренда #{ticket.rental_id}"
    if ticket.item_id:
        return f"Товар #{ticket.item_id}"
    return "Общий вопрос"

def format_support_user(user: UserOut) -> str:
    """Сформировать подпись клиента для админского уведомления."""
    username = f"@{safe(user.username)}" if user.username else "без username"
    return f"{username} · 🆔 {user.id}"

# ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
def format_new_rental_request(details: RentalDetailsOut | RentalAdminDetailsOut) -> str:
    """Сформировать уведомление админам о новой заявке."""
    rental = details.rental
    user = details.user
    item = details.item
    username = f"@{safe(user.username)}" if user.username else "—"
    delivery = "нужна" if rental.delivery_needed else "не нужна"
    address_line = f"Адрес: {safe(rental.delivery_address)}\n" if rental.delivery_needed else ""
    return (
        f"🆕 <b>Новая заявка #{rental.id}</b>\n\n"
        f"Товар: {safe(item.title)}\n"
        f"Количество: {rental.quantity}\n"
        f"Срок: {safe(rental.rental_period_text)}\n"
        f"Доставка: {delivery}\n"
        f"{address_line}\n"
        f"Клиент: {safe(rental.client_name)}\n"
        f"Телефон: {safe(rental.client_phone)}\n"
        f"Telegram: {username}\n\n"
        f"Комментарий:\n{safe(rental.client_comment)}\n\n"
        f"Статус: {escape(STATUS_LABELS.get(rental.status, rental.status.value))}"
    )

def format_user_rental_created(details: RentalDetailsOut | RentalAdminDetailsOut) -> str:
    """Сформировать подтверждение создания заявки для клиента."""
    return (
        "✅ <b>Заявка создана</b>\n\n"
        f"Товар: {safe(details.item.title)}\n"
        f"Статус: {escape(STATUS_LABELS.get(details.rental.status, details.rental.status.value))}\n"
        "Менеджер скоро свяжется с вами."
    )

def format_user_rental_status_changed(details: RentalDetailsOut | RentalAdminDetailsOut) -> str: # , old_status: RentalStatus | None = None
    """Сформировать уведомление клиенту о смене статуса заявки."""
    rental = details.rental
    item_title = safe(details.item.title)
    comment = safe(rental.manager_comment, default="")

    match rental.status:
        case RentalStatus.IN_PROGRESS:
            return f"👨‍💼 Ваша заявка №{rental.id} взята в работу.\n\nМенеджер скоро уточнит детали."
        case RentalStatus.CONFIRMED:
            return f"✅ Ваша заявка №{rental.id} подтверждена.\n\nТовар: {item_title}\nМенеджер свяжется с вами по деталям аренды."
        case RentalStatus.REJECTED:
            text = f"❌ Ваша заявка №{rental.id} отклонена."
            if comment:
                text += f"\n\nПричина/комментарий менеджера: {comment}"
            return text
        case RentalStatus.CANCELLED_BY_ADMIN:
            text = f"⚠️ Ваша заявка №{rental.id} отменена компанией."
            if comment:
                text += f"\n\nКомментарий менеджера: {comment}"
            return text
        case RentalStatus.COMPLETED:
            return f"✅ Заявка №{rental.id} завершена.\n\nСпасибо, что воспользовались арендой."
        case RentalStatus.CANCELLED_BY_CLIENT:
            return f"✅ Ваша заявка №{rental.id} отменена."
        case _:
            status = escape(STATUS_LABELS.get(rental.status, rental.status.value))
            return f"ℹ️ Статус вашей заявки №{rental.id} изменён.\n\nНовый статус: {status}"

def format_client_cancelled_rental(details: RentalDetailsOut | RentalAdminDetailsOut) -> str:
    """Сформировать уведомление админам об отмене заявки клиентом."""
    rental = details.rental
    user = details.user
    client = safe(rental.client_name) if rental.client_name else (f"@{safe(user.username)}" if user.username else f"ID {user.id}")
    return (
        f"⚠️ <b>Клиент отменил заявку №{rental.id}</b>\n\n"
        f"Клиент: {client}\n"
        f"Товар: {safe(details.item.title)}"
    )

def format_new_support_ticket(ticket: SupportTicketOut, user: UserOut) -> str:
    """Сформировать уведомление админам о новом тикете поддержки."""
    return (
        "💬 <b>Новое обращение в поддержку</b>\n\n"
        f"🎫 Тикет №{ticket.id}\n"
        #f"📅 <b>Создан:</b> {format_datetime(ticket.created_at)}\n"
        f"👤 <b>Клиент</b>: {format_support_user(user)}\n"
        f"📌 <b>Контекст:</b> {support_context(ticket)}\n"
        f"📝 <b>Сообщение:</b>\n{safe(ticket.text)}"
        #f"📄 Связанная заявка: {rental}"
    )

def format_support_user_reply(ticket: SupportTicketOut, user: UserOut, reply_text: str) -> str:
    """Сформировать уведомление админам о новом сообщении клиента в открытом тикете."""
    return (
        "💬 <b>Новое сообщение в открытом тикете</b>\n\n"
        f"🎫 <b>Тикет:</b> №{ticket.id}\n"
        f"👤 <b>Клиент:</b> {format_support_user(user)}\n"
        f"📌 <b>Контекст:</b> {support_context(ticket)}\n"
        f"📝 <b>Сообщение клиента:</b>\n{safe(reply_text)}"
    )

def format_user_support_created() -> str: # ticket: SupportTicketOut
    """Сформировать подтверждение клиенту о создании тикета поддержки."""
    return "✅ Ваше обращение отправлено в поддержку.\n\nМы ответим вам здесь, в Telegram."

def format_support_reply(ticket: SupportTicketOut, reply_text: str) -> str:
    """Сформировать сообщение клиенту с ответом поддержки."""
    return (
        f"💬 <b>Ответ поддержки по тикету №{ticket.id}</b>\n\n"
        f"{safe(reply_text)}\n\n"
        "Если нужно уточнить детали, ответьте в этот же тикет кнопкой ниже."
    )

def format_support_closed(ticket: SupportTicketOut) -> str:
    """Сформировать уведомление клиенту о закрытии тикета поддержки."""
    return f"✅ Ваше обращение №{ticket.id} закрыто.\n\nЕсли вопрос остался — создайте новое обращение командой /support."
