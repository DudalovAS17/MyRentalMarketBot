from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from services.item_service import ItemService
from states.admin import AdminStates
from keyboards.admin_kb import (
    get_admin_items_list_keyboard,
    get_admin_item_details_keyboard,
    get_admin_items_menu_keyboard,
)
from utils.functions import send_or_edit, format_price
from status.item_status import ItemStatus


admin_items_router = Router()


async def _show_items_list(
    event: Message | CallbackQuery,
    item_service: ItemService,
    state: FSMContext,
    status: ItemStatus,
    page: int,
) -> None:
    items, has_next = await item_service.admin_list_by_status(status=status, page=page)
    await state.update_data(admin_items_page=page, admin_items_status=status)

    lines = [f"📦 <b>Модерация объявлений ({status}), стр. {page}</b>\n"]

    if not items:
        lines.append("Нет объявлений в этом статусе.")
        text = "\n".join(lines)
        kb = get_admin_items_list_keyboard([], status=status, page=page, has_next=False)
        await send_or_edit(event, text, kb)
        return

    for item in items:
        price_text = format_price(item.price) if item.price is not None else "—"
        lines.append(
            f"• <b>#{item.id}</b> — {item.title} — owner_id={item.user_id} — {price_text} ₽/день"
        )

    text = "\n".join(lines)
    kb = get_admin_items_list_keyboard(items, status=status, page=page, has_next=has_next)
    await send_or_edit(event, text, kb)


def _format_item_details(item) -> str:
    price_text = format_price(item.price) if item.price is not None else "—"

    lines = [
        f"📦 <b>Объявление #{item.id}</b>\n\n"
        f"• Статус: <b>{item.status}</b>\n"
        f"• Владелец: <b>{item.user_id}</b>\n"
        f"• Название: <b>{item.title}</b>\n"
        f"• Цена: <b>{price_text} ₽/день</b>\n"
        f"• Описание: {item.description or '—'}\n"
    ]
    if item.moderation_reason:
        lines.append(f"• Причина: {item.moderation_reason}\n")
    return "".join(lines)


@admin_items_router.callback_query(F.data == "admin:items")
async def admin_items_list(callback: CallbackQuery) -> None:
    """Меню модерации объявлений."""
    await send_or_edit(
        callback,
        "📦 <b>Модерация объявлений</b>\n\nВыберите статус:",
        get_admin_items_menu_keyboard(),
    )
    await callback.answer()

@admin_items_router.callback_query(F.data.startswith("admin:items:filter:"))
async def admin_items_filter(callback: CallbackQuery, state: FSMContext, item_service: ItemService) -> None:
    """Список объявлений по статусу (страница 1)."""
    try:
        status = callback.data.split(":")[-1]
    except Exception:
        status = "PENDING"

    allowed = {"PENDING", "ACTIVE", "HIDDEN"}
    if status not in allowed:
        status = "PENDING" # типо кинем его админу в непроверенные

    await _show_items_list(callback, item_service, state, status=status, page=1)
    await callback.answer()


@admin_items_router.callback_query(F.data.startswith("admin:items:page:"))
async def admin_items_page(callback: CallbackQuery, state: FSMContext, item_service: ItemService) -> None:
    """Пагинация списка объявлений."""
    try:
        _, _, _, status, page_str = callback.data.split(":")
        page = int(page_str)
    except Exception:
        status = "PENDING"
        page = 1

    allowed = {"PENDING", "ACTIVE", "HIDDEN"}
    if status not in allowed:
        status = "PENDING"

    await _show_items_list(callback, item_service, state, status=status, page=page)
    await callback.answer()


@admin_items_router.callback_query(F.data.startswith("admin:items:view:"))
async def admin_items_view(callback: CallbackQuery, item_service: ItemService) -> None:
    """Карточка объявления."""
    try:
        item_id = int(callback.data.split(":")[-1])
    except Exception:
        await callback.answer("Некорректный ID", show_alert=True)
        return

    item = await item_service.get_item_by_id(item_id)
    if not item:
        await send_or_edit(callback, f"❌ Объявление #{item_id} не найдено.", None)
        await callback.answer()
        return

    text = _format_item_details(item)
    kb = get_admin_item_details_keyboard(item_id=item.id, status_value=item.status)
    await send_or_edit(callback, text, kb)
    await callback.answer()


@admin_items_router.callback_query(F.data.startswith("admin:items:approve:"))
async def admin_items_approve(callback: CallbackQuery, item_service: ItemService) -> None:
    """Перевод объявления в ACTIVE."""
    try:
        item_id = int(callback.data.split(":")[-1])
    except Exception:
        await callback.answer("Некорректный ID", show_alert=True)
        return

    updated = await item_service.admin_set_status(
        item_id=item_id,
        new_status="ACTIVE",
        admin_id=callback.from_user.id, # Проверка “админ ли он” уже сделана раньше
    )
    if not updated:
        await callback.answer("Нельзя изменить статус", show_alert=True)
        return

    text = _format_item_details(updated)
    kb = get_admin_item_details_keyboard(item_id=updated.id, status_value=updated.status)
    await send_or_edit(callback, text, kb)
    await callback.answer()


@admin_items_router.callback_query(F.data.startswith("admin:items:reject:"))
async def admin_items_reject_ask(callback: CallbackQuery, state: FSMContext) -> None:
    """Запрос причины отклонения объявления."""
    try:
        item_id = int(callback.data.split(":")[-1])
    except Exception:
        await callback.answer("Некорректный ID", show_alert=True)
        return

    await state.set_state(AdminStates.waiting_item_reject_reason)
    await state.update_data(admin_item_id=item_id)
    await send_or_edit(callback, f"❌ Укажите причину отклонения объявления #{item_id}:", None)
    await callback.answer()


@admin_items_router.message(AdminStates.waiting_item_reject_reason)
async def admin_items_reject_apply(message: Message, state: FSMContext, item_service: ItemService) -> None:
    """Применяет отклонение объявления с причиной."""
    data = await state.get_data()
    item_id = data.get("admin_item_id")
    reason = (message.text or "").strip()
    if not item_id:
        await state.clear()
        await message.answer("❌ Не удалось определить объявление для отклонения.")
        return
    if not reason:
        await message.answer("❌ Причина не может быть пустой. Введите текст причины:")
        return

    await state.clear()
    updated = await item_service.admin_set_status(
        item_id=item_id,
        new_status="REJECTED",
        admin_id=message.from_user.id,
        reason=reason,
    )
    if not updated:
        await message.answer("❌ Нельзя изменить статус.")
        return

    text = _format_item_details(updated)
    kb = get_admin_item_details_keyboard(item_id=updated.id, status_value=updated.status)
    await send_or_edit(message, text, kb)



@admin_items_router.callback_query(F.data.startswith("admin:items:hide:"))
async def admin_items_hide(callback: CallbackQuery, item_service: ItemService) -> None:
    """Скрыть объявление (ACTIVE -> HIDDEN)."""
    try:
        item_id = int(callback.data.split(":")[-1])
    except Exception:
        await callback.answer("Некорректный ID", show_alert=True)
        return

    updated = await item_service.admin_set_status(
        item_id=item_id,
        new_status="HIDDEN",
        admin_id=callback.from_user.id,
    )
    if not updated:
        await callback.answer("Нельзя изменить статус", show_alert=True)
        return

    text = _format_item_details(updated)
    kb = get_admin_item_details_keyboard(item_id=updated.id, status_value=updated.status)
    await send_or_edit(callback, text, kb)
    await callback.answer()


@admin_items_router.callback_query(F.data.startswith("admin:items:unhide:"))
async def admin_items_unhide(callback: CallbackQuery, item_service: ItemService) -> None:
    """Вернуть объявление (HIDDEN -> ACTIVE)."""
    try:
        item_id = int(callback.data.split(":")[-1])
    except Exception:
        await callback.answer("Некорректный ID", show_alert=True)
        return

    updated = await item_service.admin_set_status(
        item_id=item_id,
        new_status="ACTIVE",
        admin_id=callback.from_user.id,
    )
    if not updated:
        await callback.answer("Нельзя изменить статус", show_alert=True)
        return

    text = _format_item_details(updated)
    kb = get_admin_item_details_keyboard(item_id=updated.id, status_value=updated.status)
    await send_or_edit(callback, text, kb)
    await callback.answer()