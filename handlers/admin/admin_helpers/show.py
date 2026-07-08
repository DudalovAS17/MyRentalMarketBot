from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from services.admin_rental_service import AdminRentalService
from services.item_service import ItemService
from services.user_service import UserService
from services.support_service import SupportService

from .keyboard import (get_admin_deals_list_keyboard, get_admin_deal_details_keyboard, get_admin_items_list_keyboard,
                       get_admin_user_card_keyboard, get_admin_support_ticket_keyboard, get_admin_support_list_keyboard)
from .texts import format_deal_details, format_user_card, format_ticket_card, format_datetime

from utils.functions import send_or_edit
from utils.validators import format_price
from status.item_status import ItemStatus
from utils.errors import ServiceError

# ──────────────────────────────────────────────────   ─────────────────────────────────────────────────────────────
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

# ────────────────────────────────────────────────── items moderation ─────────────────────────────────────────────────────────────
# Показать список объявлений
async def show_items_list(
    event: Message | CallbackQuery,
    item_service: ItemService,
    state: FSMContext,
    status: ItemStatus,
    page: int,
) -> None:
    """Показать список товаров по статусу для управления каталогом."""

    try:
        items, has_next = await item_service.admin_list_by_status(status=status, page=page)
    except ServiceError:
        #await send_reply(event, "⚠️ Не удалось загрузить список товаров. Попробуйте позже.")
        return

    await state.update_data(admin_items_page=page, admin_items_status=status) # status.value

    lines = [f"📦 <b>Модерация товаров ({status.value}), стр. {page}</b>\n"]

    if not items:
        lines.append("Нет товаров в этом статусе.")
        await send_or_edit(
            event,
            "\n".join(lines),
            get_admin_items_list_keyboard([], status=status.value, page=page, has_next=False)
        )
        return

    for item in items:
        price_text = format_price(item.price) if item.price is not None else "—"
        lines.append(
            f"• <b>#{item.id}</b> — {item.title} — {price_text} ₽"
        )

    await send_or_edit(
        event,
        "\n".join(lines),
        get_admin_items_list_keyboard(items, status=status.value, page=page, has_next=has_next)
    )

# ────────────────────────────────────────────────── users ─────────────────────────────────────────────────────────────
async def show_user_card(event: Message | CallbackQuery, user_service: UserService, user_id: int) -> None:
    """Показать карточку пользователя в админке"""

    user = await user_service.get_by_id(user_id)
    if not user:
        await send_or_edit(event, f"❌ Пользователь #{user_id} не найден.", None)
        return

    await send_or_edit(
        event,
        format_user_card(user),
        get_admin_user_card_keyboard(user.id, user.account_status)
    )


# ───────────────────────────────────────────────── support ─────────────────────────────────────────────────────────────
async def show_support_ticket_list(
        event: Message | CallbackQuery,
        user_service: UserService,
        support_service: SupportService,
        page: int,
        kind: str,
) -> None:
    """Показать список открытых тикетов поддержки"""

    tickets, has_next = await support_service.list_open_tickets(page, kind=kind)

    title_by_kind = {
        "items": "📦 Вопросы по товарам",
        "rentals": "📄 Вопросы по арендам",
        "general": "🆘 Общие обращения",
    }
    title = title_by_kind.get(kind, "🆘 Обращения")
    lines = [f"📭 <b>{title}</b> (стр. {page})\n"]

    if not tickets:
        lines.append("Пока нет открытых тикетов.")
    else:
        for ticket in tickets:
            created_at = format_datetime(ticket.created_at)

            ticket_user = await user_service.get_by_id(ticket.user_id)
            if ticket_user and ticket_user.username:
                uname = f"@{ticket_user.username}"
            elif ticket_user:
                uname = f"user_id={ticket.user_id}"
            else:
                #uname = f"tg_id={ticket_user.telegram_id}"
                uname = f"user_id={ticket.user_id}"

            if ticket.item_id:
                context = f"товар #{ticket.item_id}"
            elif ticket.rental_id:
                context = f"аренда #{ticket.rental_id}"
            else:
                context = "общий вопрос"

            lines.append(f"•🎫• <b>#{ticket.id}</b> — {context} — {uname} — {created_at}")

    rows = [{"ticket": ticket} for ticket in tickets]
    await send_or_edit(
        event,
        "\n".join(lines),
        get_admin_support_list_keyboard(rows, page=page, has_next=has_next, kind=kind),
    )

async def show_support_ticket_card_or_not_found(
    event: Message | CallbackQuery,
    user_service: UserService,
    support_service: SupportService,
    ticket_id: int,
) -> None: #SupportTicketOut | None:
    """Показать карточку тикета или not-found сообщение"""

    ticket = await support_service.get_ticket_by_id(ticket_id)
    if not ticket:
        await send_or_edit(event, f"❌ Тикет #{ticket_id} не найден.", None)
        return #None

    ticket_user = await user_service.get_by_id(ticket.user_id)
    await send_or_edit(
        event,
        format_ticket_card(ticket, ticket_user),
        get_admin_support_ticket_keyboard(ticket.id, ticket.status),
    )

    #return ticket

# ──────────────────────────────────────────────────   ─────────────────────────────────────────────────────────────
