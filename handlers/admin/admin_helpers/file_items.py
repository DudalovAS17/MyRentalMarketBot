from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from services.item_service import ItemService

from .keyboard import get_admin_items_list_keyboard, get_admin_item_details_keyboard
from status.item_status import ItemStatus
from utils.functions import send_or_edit, format_price
from utils.errors import ServiceError

# ────────────────────────────────────────────────── parse ─────────────────────────────────────────────────────────────
async def get_admin_item_id_or_alert(callback: CallbackQuery) -> int | None:
    """Получить item_id из callback data или показать alert"""
    try:
        return int((callback.data or "").split(":")[-1])
    except (ValueError, IndexError):
        await callback.answer("Некорректный ID товара", show_alert=True)
        return None


# ────────────────────────────────────────────────── texts ─────────────────────────────────────────────────────────────
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

# ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
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

async def apply_item_status_action(
    event: Message | CallbackQuery,
    item_service: ItemService,
    item_id: int,
    new_status: ItemStatus
) -> None:
    """Применить admin status-action к товару и перерисовать карточку"""
    updated = await item_service.admin_set_status(
        item_id=item_id,
        new_status=new_status,
        updated_by_admin_id=None, #event.from_user.id
    )
    if not updated:
        if isinstance(event, CallbackQuery):
            await event.answer("Нельзя изменить статус товара", show_alert=True)
        else:
            await event.answer("❌ Нельзя изменить статус товара.")
        return

    await send_or_edit(
        event,
        format_item_details(updated),
        get_admin_item_details_keyboard(item_id=updated.id, status_value=updated.status) # updated.status.value
    )