from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from services.item_service import ItemService
from .admin_helpers.validate import parse_admin_item_status
from .admin_helpers.file_items import format_item_details, apply_item_status_action, show_items_list, get_admin_item_id_or_alert

from states.admin import AdminStates
from admin_helpers.keyboard import get_admin_item_details_keyboard, get_admin_items_menu_keyboard
from utils.functions import send_or_edit
from status.item_status import ItemStatus

admin_items_router = Router()

# ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
@admin_items_router.callback_query(F.data == "admin:items")
async def admin_items_list(callback: CallbackQuery) -> None:
    """Меню модерации объявлений"""
    await callback.answer()

    await send_or_edit(
        callback,
        "📦 <b>Модерация объявлений</b>\n\nВыберите статус:",
        get_admin_items_menu_keyboard()
    )

@admin_items_router.callback_query(F.data.startswith("admin:items:filter:"))
async def admin_items_filter(callback: CallbackQuery, state: FSMContext, item_service: ItemService) -> None:
    """Список объявлений по статусу (страница 1)"""
    await callback.answer()

    raw_status = (callback.data or "").split(":")[-1]
    status = parse_admin_item_status(raw_status)

    await show_items_list(callback, item_service, state, status=status, page=1)

@admin_items_router.callback_query(F.data.startswith("admin:items:page:"))
async def admin_items_page(callback: CallbackQuery, state: FSMContext, item_service: ItemService) -> None:
    """Пагинация списка объявлений"""
    await callback.answer()

    try:
        _, _, _, raw_status, page_str = (callback.data or "").split(":")
        status = parse_admin_item_status(raw_status)
        page = int(page_str)
    except (ValueError, IndexError):
        status = ItemStatus.PENDING
        page = 1

    await show_items_list(callback, item_service, state, status=status, page=page)

@admin_items_router.callback_query(F.data.startswith("admin:items:view:"))
async def admin_items_view(callback: CallbackQuery, item_service: ItemService) -> None:
    """Карточка объявления"""
    await callback.answer()

    item_id = await get_admin_item_id_or_alert(callback)
    if item_id is None:
        return

    item = await item_service.get_item_by_id(item_id)
    if not item:
        await send_or_edit(callback, f"❌ Объявление #{item_id} не найдено.", None)
        return

    await send_or_edit(
        callback,
        format_item_details(item),
        get_admin_item_details_keyboard(item_id=item.id, status_value=item.status)
    )

@admin_items_router.callback_query(F.data.startswith("admin:items:approve:"))
async def admin_items_approve(callback: CallbackQuery, item_service: ItemService) -> None:
    """Перевод объявления в ACTIVE"""
    await callback.answer()

    item_id = await get_admin_item_id_or_alert(callback)
    if item_id is None:
        return

    await apply_item_status_action(callback, item_service, item_id, new_status=ItemStatus.ACTIVE)


# ────────────────────────────────────────── Отклонение объявления ─────────────────────────────────────────────────────
@admin_items_router.callback_query(F.data.startswith("admin:items:reject:"))
async def admin_items_reject_ask(callback: CallbackQuery, state: FSMContext) -> None:
    """Запрос причины отклонения объявления"""
    await callback.answer()

    item_id = await get_admin_item_id_or_alert(callback)
    if item_id is None:
        return

    await state.set_state(AdminStates.waiting_item_reject_reason)
    await state.update_data(admin_item_id=item_id)

    await send_or_edit(
        callback,
        f"❌ Укажите причину отклонения объявления #{item_id}:",
        None
    )

@admin_items_router.message(AdminStates.waiting_item_reject_reason)
async def admin_items_reject_apply(message: Message, state: FSMContext, item_service: ItemService) -> None:
    """Применяет отклонение объявления с причиной"""
    data = await state.get_data()

    item_id = data.get("admin_item_id")
    if not item_id:
        await state.clear()
        await message.answer("❌ Не удалось определить объявление для отклонения.")
        return

    reason = (message.text or "").strip()
    if not reason:
        await message.answer("❌ Причина не может быть пустой. Введите текст причины:")
        return

    await state.clear()

    await apply_item_status_action(message, item_service, item_id, new_status=ItemStatus.REJECTED, reason=reason)


# ────────────────────────────────────── Скрыть объявление / Вернуть объявление ────────────────────────────────────────
@admin_items_router.callback_query(F.data.startswith("admin:items:hide:"))
async def admin_items_hide(callback: CallbackQuery, item_service: ItemService) -> None:
    """Скрыть объявление (ACTIVE -> HIDDEN)"""
    await callback.answer()

    item_id = await get_admin_item_id_or_alert(callback)
    if item_id is None:
        return

    await apply_item_status_action(callback, item_service, item_id, new_status=ItemStatus.HIDDEN)

@admin_items_router.callback_query(F.data.startswith("admin:items:unhide:"))
async def admin_items_unhide(callback: CallbackQuery, item_service: ItemService) -> None:
    """Вернуть объявление (HIDDEN -> ACTIVE)"""
    await callback.answer()

    item_id = await get_admin_item_id_or_alert(callback)
    if item_id is None:
        return

    await apply_item_status_action(callback, item_service, item_id, new_status=ItemStatus.ACTIVE)


# ─────────────────────────────────────────────────────────────────────────────────────────────────────
"""Переписать - см. файл show.py
@items_router.callback_query(F.data.startswith(SHOW_ITEM_CB))
async def show_item_details(
        callback: CallbackQuery,
        state: FSMContext,
        item_service: ItemService,
        category_service: CategoryService
) -> None:
    ""Показывает детали товара""
    await callback.answer()

    item = await ch.load_item(
        callback, item_service.get_item_by_id, parse_callback(callback.data, SHOW_ITEM_CB), invalid_id_text=ch.not_item_id,
        load_error_text=ch.serv_err_item, not_found_text=ch.not_item, markup_back=ch.build_back_to_my_items_keyboard()
    )
    if item is None:
        return

    await ch.store_selected_item(state, item.id)

    category_name, subcategory_name = await ch.load_item_category_context(
        category_service=category_service, item=item)

    await send_or_edit(
        callback,
        ch.item_details_text(item, category_name, subcategory_name),
        markup=build_my_item_details_keyboard(item)
    )
"""