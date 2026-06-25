from aiogram.types import CallbackQuery, Message

from services.admin_rental_service import AdminRentalService
from status.rental_status import RentalStatus
from schemas.rental import RentalAdminDetailsOut
from .keyboard import get_admin_deals_list_keyboard, get_admin_deal_details_keyboard
from utils.functions import send_or_edit

def parse_admin_page(raw: str | None, *, default: int = 1) -> int:
    """Распарсить номер страницы из admin callback data"""
    try:
        page = int((raw or "").split(":")[-1])
    except (ValueError, IndexError):
        return default
    return max(1, page)

def parse_admin_rental_id(raw: str | None) -> int | None:
    """Распарсить rental_id из admin callback data"""
    try:
        return int((raw or "").split(":")[-1])
    except (ValueError, IndexError):
        return None

def parse_admin_rental_id_text(raw: str | None) -> int | None:
    """Распарсить rental_id из текстового ввода админа"""
    try:
        return int((raw or "").strip())
    except (ValueError, TypeError):
        return None

def format_user_line(label: str, user) -> str:
    """Сформировать строку пользователя для карточки заявки"""
    if not user:
        return f"{label}: <i>не найден</i>"
    tg = user.telegram_id
    username = user.username
    return f"{label}: id={user.id}, tg={tg}, @{username}"

def format_deal_details(details: RentalAdminDetailsOut) -> str:
    """Сформировать текст карточки сделки для админки"""
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

async def show_deals_list(event: Message | CallbackQuery, admin_rental_service: AdminRentalService, page: int) -> None:
    """Показать список последних заявок в админке"""
    rows, has_next = await admin_rental_service.list_recent_rentals(page=page)
    #await state.update_data(admin_deals_page=page)

    lines = [f"📄 <b>Заявки на аренду (последние), стр. {page}</b>\n"]

    if not rows:
        await send_or_edit(
            event,
            "Пока нет заявок. \n".join(lines),
            get_admin_deals_list_keyboard([], page=page, has_next=False)
        )
        return

    for row in rows:
        r = row.rental
        item = row.item
        lines.append(f"• <b>#{r.id}</b> — {r.status.value} — {item.title} - item_id={r.item_id}")

    await send_or_edit(
        event,
        "\n".join(lines),
        get_admin_deals_list_keyboard(rows, page=page, has_next=has_next)
    )


def parse_resolve_target_callback(raw: str | None) -> tuple[int, str] | None:
    """Распарсить rental_id и target из callback закрытия спора"""
    parts = (raw or "").split(":")
    if len(parts) < 5:
        return None
    try:
        rental_id = int(parts[3])
        target = parts[4]
    except ValueError:
        return None
    return rental_id, target


def parse_dispute_target(raw_target: str) -> RentalStatus | None:
    """Преобразовать строковый target закрытия спора в RentalStatus"""
    target_map = {
        "active": RentalStatus.ACTIVE,
        "completed": RentalStatus.COMPLETED,
        "confirmed": RentalStatus.CONFIRMED,
    }
    return target_map.get(raw_target)


# пока не реализовано
async def show_deal_card(
    event: Message | CallbackQuery,
    admin_rental_service: AdminRentalService,
    rental_id: int,
    prefix_text: str = "",
) -> None:
    """Показать карточку сделки в админке"""
    details = await admin_rental_service.get_details(rental_id)
    if not details:
        await send_or_edit(event, f"❌ Сделка #{rental_id} не найдена.", None)
        return

    await send_or_edit(
        event,
        f"{prefix_text}{format_deal_details(details)}",
        get_admin_deal_details_keyboard(rental_id=rental_id, status=details.rental.status)
    )
