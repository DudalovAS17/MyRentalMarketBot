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

# ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
def format_new_rental_request(details: RentalDetailsOut | RentalAdminDetailsOut) -> str:
    """Сформировать уведомление админам о новой заявке."""
    rental = details.rental
    user = details.user
    item = details.item
    username = f"@{safe(user.username)}" if user.username else "—"
    period = safe(rental.rental_period_text)
    comment = safe(rental.client_comment)
    return (
        "🔔 <b>Новая заявка на аренду</b>\n\n"
        f"🆕 Заявка №{rental.id}\n"
        f"Клиент: {safe(rental.client_name) or username}\n"
        f"Telegram: {username}\n"
        f"Телефон: {safe(rental.client_phone)}\n"
        f"Товар: {safe(item.title)}\n"
        f"Период: {period}\n"
        f"Комментарий: {comment}\n\n"
        "Откройте админку для обработки."
    )

def format_user_rental_created(details: RentalDetailsOut | RentalAdminDetailsOut) -> str:
    """Сформировать подтверждение создания заявки для клиента."""
    return (
        "✅ <b>Заявка создана</b>\n\n"
        f"Товар: {safe(details.item.title)}\n"
        f"Статус: {escape(STATUS_LABELS.get(details.rental.status, details.rental.status.value))}\n"
        "Менеджер скоро свяжется с вами."
    )

def format_user_rental_status_changed(details: RentalDetailsOut | RentalAdminDetailsOut, old_status: RentalStatus | None = None) -> str:
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
    username = f"@{safe(user.username)} (🆔 id={user.id})" if user.username else "—"
    rental = f"#{ticket.rental_id}" if ticket.rental_id else "—"
    return (
        "💬 <b>Новое обращение в поддержку</b>\n\n"
        f"🎫 Тикет №{ticket.id}\n"
        #f"📅 <b>Создан:</b> {format_datetime(ticket.created_at)}\n"
        f"👤 <b>Клиент</b>: {username}\n"
        f"📝 <b>Текст:</b>: {safe(ticket.text)}\n"
        f"📄 Связанная заявка: {rental}"
    )

def format_user_support_created(ticket: SupportTicketOut) -> str:
    """Сформировать подтверждение клиенту о создании тикета поддержки."""
    return "✅ Ваше обращение отправлено в поддержку.\n\nМы ответим вам здесь, в Telegram."

def format_support_reply(ticket: SupportTicketOut, reply_text: str) -> str:
    """Сформировать сообщение клиенту с ответом поддержки."""
    return f"💬 <b>Ответ поддержки</b>\n\n{safe(reply_text)}"

def format_support_closed(ticket: SupportTicketOut) -> str:
    """Сформировать уведомление клиенту о закрытии тикета поддержки."""
    return f"✅ Ваше обращение №{ticket.id} закрыто.\n\nЕсли вопрос остался — создайте новое обращение командой /support."
