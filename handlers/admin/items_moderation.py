from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from services.item_service import ItemService
from .admin_helpers.keyboard import get_admin_item_details_keyboard, get_admin_items_menu_keyboard
from .admin_helpers.parse import get_admin_item_id_or_alert, parse_admin_item_status
from .admin_helpers.show import show_items_list
from .admin_helpers.texts import format_item_details

from utils.functions import send_or_edit
from status.item_status import ItemStatus

admin_items_router = Router()

# ***** кнопка админки "Модерация товаров" *****

@admin_items_router.callback_query(F.data == "admin:items")
async def admin_items_list(callback: CallbackQuery) -> None:
    """Меню модерации товаров"""
    await callback.answer()

    await send_or_edit(
        callback,
        "📦 <b>Модерация товаров</b>\n\nВыберите действие:",
        get_admin_items_menu_keyboard()
    )

@admin_items_router.callback_query(F.data.startswith("admin:items:filter:"))
async def admin_items_filter(callback: CallbackQuery, state: FSMContext, item_service: ItemService) -> None:
    """Список товаров по статусу (страница 1)"""
    await callback.answer()

    raw_status = (callback.data or "").split(":")[-1]
    status = parse_admin_item_status(raw_status)

    await show_items_list(callback, item_service, state, status=status, page=1)

@admin_items_router.callback_query(F.data.startswith("admin:items:page:"))
async def admin_items_page(callback: CallbackQuery, state: FSMContext, item_service: ItemService) -> None:
    """Пагинация списка товаров"""
    await callback.answer()

    try:
        _, _, _, raw_status, page_str = (callback.data or "").split(":")
        status = parse_admin_item_status(raw_status)
        page = int(page_str)
    except (ValueError, IndexError):
        status = ItemStatus.DRAFT
        page = 1

    await show_items_list(callback, item_service, state, status=status, page=page)

@admin_items_router.callback_query(F.data.startswith("admin:items:view:"))
async def admin_items_view(callback: CallbackQuery, item_service: ItemService) -> None:
    """Карточка товара"""
    await callback.answer()

    item_id = await get_admin_item_id_or_alert(callback)
    if item_id is None:
        return

    item = await item_service.get_item_by_id(item_id)
    if not item:
        await send_or_edit(callback, f"❌ Товар #{item_id} не найден.", None)
        return

    await send_or_edit(
        callback,
        format_item_details(item),
        get_admin_item_details_keyboard(item_id=item.id, status_value=item.status)
    )

# ───────────── "Активируем" товар ─────────────
@admin_items_router.callback_query(F.data.startswith("admin:items:approve:"))
async def admin_items_approve(callback: CallbackQuery, item_service: ItemService) -> None:
    """Перевод товара в ACTIVE"""
    await callback.answer()

    item_id = await get_admin_item_id_or_alert(callback)
    if item_id is None:
        return

    await apply_item_status_action(callback, item_service, item_id, new_status=ItemStatus.ACTIVE)

# ───────────── Скрыть товар ─────────────
@admin_items_router.callback_query(F.data.startswith("admin:items:hide:"))
async def admin_items_hide(callback: CallbackQuery, item_service: ItemService) -> None:
    """Скрыть товар (ACTIVE -> HIDDEN)"""
    await callback.answer()

    item_id = await get_admin_item_id_or_alert(callback)
    if item_id is None:
        return

    await apply_item_status_action(callback, item_service, item_id, new_status=ItemStatus.HIDDEN)

# ───────────── Вернуть товар ─────────────
@admin_items_router.callback_query(F.data.startswith("admin:items:unhide:"))
async def admin_items_unhide(callback: CallbackQuery, item_service: ItemService) -> None:
    """Вернуть товар (HIDDEN -> ACTIVE)"""
    await callback.answer()

    item_id = await get_admin_item_id_or_alert(callback)
    if item_id is None:
        return

    await apply_item_status_action(callback, item_service, item_id, new_status=ItemStatus.ACTIVE)

# ───────────── Архивируем товар ─────────────
@admin_items_router.callback_query(F.data.startswith("admin:items:archive:"))
async def admin_items_archive(callback: CallbackQuery, item_service: ItemService) -> None:
    """Убрать товар в архив (DRAFT/ACTIVE/HIDDEN -> ARCHIVED)."""
    await callback.answer()

    item_id = await get_admin_item_id_or_alert(callback)
    if item_id is None:
        return

    await apply_item_status_action(callback, item_service, item_id, new_status=ItemStatus.ARCHIVED)


# ──────────────────────────────────────────────── helpers ─────────────────────────────────────────────────────────────
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