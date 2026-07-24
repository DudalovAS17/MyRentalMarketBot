from typing import Any
from decimal import Decimal, InvalidOperation
from collections.abc import Awaitable, Callable
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from services.item_service import ItemService
from services.admin_service import AdminActionService
from .admin_helpers.keyboard import get_admin_item_details_keyboard, get_admin_items_menu_keyboard
from .admin_helpers.parse import get_admin_item_id_or_alert, parse_admin_item_status
from .admin_helpers.show import show_items_list
from .admin_helpers.texts import format_item_details

from status.item_status import ItemStatus
from schemas.item import ItemUpdate
from states.admin import AdminStates
from utils.functions import send_or_edit
from utils.callbacks import (ADMIN_ITEMS_MOD, ADMIN_ITEMS_MOD_FILTER, ADMIN_ITEMS_MOD_PAGE, ADMIN_ITEMS_MOD_VIEW,
                             ADMIN_ITEMS_MOD_APPROVE, ADMIN_ITEMS_MOD_HIDE, ADMIN_ITEMS_MOD_UNHIDE, ADMIN_ITEMS_MOD_ARCHIVE,
                             ADMIN_ITEMS_MOD_FIND, ADMIN_ITEMS_MOD_EDIT_QUANTITY, ADMIN_ITEMS_MOD_EDIT_PRICE)

admin_items_router = Router()

# ***** кнопка админки "Модерация товаров" *****

AdminItemAction = Callable[..., Awaitable[Any]]

@admin_items_router.callback_query(F.data == ADMIN_ITEMS_MOD)
async def admin_items_list(callback: CallbackQuery) -> None:
    """Меню модерации товаров"""
    await callback.answer()


    await send_or_edit(
        callback,
        "📦 <b>Модерация товаров</b>\n\nВыберите действие:",
        get_admin_items_menu_keyboard()
    )

@admin_items_router.callback_query(F.data.startswith(ADMIN_ITEMS_MOD_FILTER))
async def admin_items_filter(callback: CallbackQuery, state: FSMContext, item_service: ItemService) -> None:
    """Список товаров по статусу (страница 1)"""
    await callback.answer()

    raw_status = (callback.data or "").split(":")[-1]
    status = parse_admin_item_status(raw_status)

    await show_items_list(callback, item_service, state, status=status, page=1)

@admin_items_router.callback_query(F.data.startswith(ADMIN_ITEMS_MOD_PAGE))
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

@admin_items_router.callback_query(F.data.startswith(ADMIN_ITEMS_MOD_VIEW))
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


# ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
# ───────────── "Активируем" товар ─────────────
@admin_items_router.callback_query(F.data.startswith(ADMIN_ITEMS_MOD_APPROVE))
async def admin_items_approve(callback: CallbackQuery, item_service: ItemService, admin_service: AdminActionService, admin) -> None:
    """Перевод товара в ACTIVE"""
    await callback.answer()

    item_id = await get_admin_item_id_or_alert(callback)
    if item_id is None:
        return

    await apply_item_status_action(callback, item_service, admin_service, admin, item_id, action_name="Опубликовать",
                                   service_call=item_service.admin_publish_item) # new_status=ItemStatus.ACTIVE

# ───────────── Скрыть товар ─────────────
@admin_items_router.callback_query(F.data.startswith(ADMIN_ITEMS_MOD_HIDE))
async def admin_items_hide(callback: CallbackQuery, item_service: ItemService, admin_service: AdminActionService, admin) -> None:
    """Скрыть товар (ACTIVE -> HIDDEN)"""
    await callback.answer()

    item_id = await get_admin_item_id_or_alert(callback)
    if item_id is None:
        return

    await apply_item_status_action(callback, item_service, admin_service, admin, item_id, action_name="Скрыть",
                                   service_call=item_service.admin_hide_item) # new_status=ItemStatus.HIDDEN

# ───────────── Вернуть товар ─────────────
@admin_items_router.callback_query(F.data.startswith(ADMIN_ITEMS_MOD_UNHIDE))
async def admin_items_unhide(callback: CallbackQuery, item_service: ItemService, admin_service: AdminActionService, admin) -> None:
    """Вернуть товар (HIDDEN -> ACTIVE)"""
    await callback.answer()

    item_id = await get_admin_item_id_or_alert(callback)
    if item_id is None:
        return

    await apply_item_status_action(callback, item_service, admin_service, admin, item_id, action_name="Вернуть в каталог",
                                   service_call=item_service.admin_unhide_item) # new_status=ItemStatus.ACTIVE

# ───────────── Архивируем товар ─────────────
@admin_items_router.callback_query(F.data.startswith(ADMIN_ITEMS_MOD_ARCHIVE))
async def admin_items_archive(callback: CallbackQuery, item_service: ItemService, admin_service: AdminActionService, admin) -> None:
    """Убрать товар в архив (DRAFT/ACTIVE/HIDDEN -> ARCHIVED)."""
    await callback.answer()

    item_id = await get_admin_item_id_or_alert(callback)
    if item_id is None:
        return

    await apply_item_status_action(callback, item_service, admin_service, admin, item_id, action_name="Архивировать",
                                   service_call=item_service.admin_archive_item) # new_status=ItemStatus.ARCHIVED

# helper
async def apply_item_status_action(
    event: Message | CallbackQuery,
    item_service: ItemService,
    admin_service: AdminActionService,
    admin,
    item_id: int,
    #new_status: ItemStatus
    action_name: str,
    service_call: AdminItemAction,
) -> None:
    """Применить admin status-action к товару и перерисовать карточку"""

    updated = await service_call(
        item_id,
        updated_by_admin_id=None, #event.from_user.id
    )
    # updated = await item_service.admin_set_status(
    #     item_id=item_id,
    #     new_status=new_status,
    #     updated_by_admin_id=None, #event.from_user.id
    # )
    if not updated:
        if isinstance(event, CallbackQuery):
            await event.answer(f"Нельзя выполнить действие: {action_name}.", show_alert=True) # "Нельзя изменить статус товара"
        else:
            await event.answer(f"❌ Нельзя выполнить действие: {action_name}.") # "❌ Нельзя изменить статус товара."
        return

    await admin_service.log_item_status_change(
        admin_tg_id=event.from_user.id,
        admin_id=getattr(admin, "id", None),
        entity_id=item_id,
        new_status=updated.status #new_status,
    )

    await send_or_edit(
        event,
        format_item_details(updated), # updated.id
        get_admin_item_details_keyboard(item_id=updated.id, status_value=updated.status) # updated.status.value
    )


# ─────────────────────────────────────────── Изменения параметров товара ──────────────────────────────────────────────
async def show_admin_item_card(event: Message | CallbackQuery, item_service: ItemService, item_id: int) -> None:
    """Показать админскую карточку товара с действиями управления."""
    item = await item_service.get_item_by_id(item_id)
    if not item:
        await send_or_edit(event, f"❌ Товар #{item_id} не найден.", None)
        return

    await send_or_edit(
        event,
        format_item_details(item),
        get_admin_item_details_keyboard(item_id=item.id, status_value=item.status)
    )

# ────── FSM-поиск товара в админке ───────
@admin_items_router.callback_query(F.data == ADMIN_ITEMS_MOD_FIND)
async def admin_items_find(callback: CallbackQuery, state: FSMContext) -> None:
    """Запросить ID товара для быстрого открытия карточки."""
    await callback.answer()
    await state.set_state(AdminStates.waiting_item_find_id)
    await send_or_edit(callback, "🔎 Введите ID товара, который нужно открыть:", None)

@admin_items_router.message(AdminStates.waiting_item_find_id)
async def admin_items_find_by_id(message: Message, state: FSMContext, item_service: ItemService) -> None:
    """Открыть админскую карточку товара по введённому ID."""
    try:
        item_id = int((message.text or "").strip())
    except ValueError:
        await message.answer("❌ Введите числовой ID товара.")
        return

    await state.clear()
    await show_admin_item_card(message, item_service, item_id)

# ────── FSM-изменения количества товара в админке ───────
@admin_items_router.callback_query(F.data.startswith(ADMIN_ITEMS_MOD_EDIT_QUANTITY))
async def admin_items_edit_quantity(callback: CallbackQuery, state: FSMContext) -> None:
    """Запросить новое доступное количество товара."""
    await callback.answer()
    item_id = await get_admin_item_id_or_alert(callback)
    if item_id is None:
        return
    await state.update_data(admin_edit_item_id=item_id)
    await state.set_state(AdminStates.waiting_item_quantity)
    await send_or_edit(callback, f"📦 Введите новое доступное количество для товара #{item_id}:", None)

@admin_items_router.message(AdminStates.waiting_item_quantity)
async def admin_items_save_quantity(message: Message, state: FSMContext, item_service: ItemService, user) -> None:
    """Сохранить новое доступное количество товара."""
    try:
        quantity = int((message.text or "").strip())
        if quantity < 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введите целое число 0 или больше.")
        return

    data = await state.get_data()
    item_id = data.get("admin_edit_item_id")
    if item_id is None:
        await message.answer("❌ Не удалось определить товар. Повторите попытку.")
        return

    await state.clear()

    # Обновить доступное количество товар
    updated = await item_service.update(item_id, ItemUpdate(available_quantity=quantity), updated_by_admin_id=getattr(user, "id", None))
    if not updated:
        await message.answer(f"❌ Товар #{item_id} не найден.")
        return

    await send_or_edit(message, format_item_details(updated), get_admin_item_details_keyboard(item_id=updated.id, status_value=updated.status))

# ────── FSM-изменения цены товара в админке ───────
@admin_items_router.callback_query(F.data.startswith(ADMIN_ITEMS_MOD_EDIT_PRICE))
async def admin_items_edit_price(callback: CallbackQuery, state: FSMContext) -> None:
    """Запросить новую цену товара."""
    await callback.answer()
    item_id = await get_admin_item_id_or_alert(callback)
    if item_id is None:
        return

    await state.update_data(admin_edit_item_id=item_id)
    await state.set_state(AdminStates.waiting_item_price)

    await send_or_edit(callback, f"💰 Введите новую цену за день для товара #{item_id}:", None)

@admin_items_router.message(AdminStates.waiting_item_price)
async def admin_items_save_price(message: Message, state: FSMContext, item_service: ItemService, user) -> None:
    """Сохранить новую цену товара."""
    raw = (message.text or "").strip().replace(" ", "").replace(",", ".")
    try:
        price = Decimal(raw)
        if price < 0:
            raise ValueError
    except (InvalidOperation, ValueError):
        await message.answer("❌ Введите цену числом, например 1500 или 1500.50.")
        return

    data = await state.get_data()
    item_id = data.get("admin_edit_item_id")
    if item_id is None:
        await message.answer("❌ Не удалось определить товар. Повторите попытку.")
        return

    await state.clear()

    # Обновить цену товара
    updated = await item_service.update(item_id, ItemUpdate(price=price), updated_by_admin_id=getattr(user, "id", None))
    if not updated:
        await message.answer(f"❌ Товар #{item_id} не найден.")
        return

    await send_or_edit(message, format_item_details(updated), get_admin_item_details_keyboard(item_id=updated.id, status_value=updated.status))


