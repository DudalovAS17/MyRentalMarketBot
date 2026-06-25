from aiogram.types import CallbackQuery, Message

from services.admin_rental_service import AdminRentalService
from .keyboard import get_admin_deals_list_keyboard, get_admin_deal_details_keyboard
from .texts import format_deal_details
from utils.functions import send_or_edit

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

# пока не реализовано
async def show_deal_card(
    event: Message | CallbackQuery,
    admin_rental_service: AdminRentalService,
    rental_id: int,
    prefix_text: str = "",
) -> None:
    """Показать карточку заявки в админке"""
    details = await admin_rental_service.get_details(rental_id)
    if not details:
        await send_or_edit(event, f"❌ Заявка #{rental_id} не найдена.", None)
        return

    await send_or_edit(
        event,
        f"{prefix_text}{format_deal_details(details)}", # f"✅ {action_name}.\n\n" + format_deal_details(details)
        get_admin_deal_details_keyboard(rental_id=rental_id, status=details.rental.status)
    )