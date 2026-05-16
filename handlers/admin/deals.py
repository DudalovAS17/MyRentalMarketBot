from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from services.admin_rental_service import AdminRentalService
from .admin_helpers.file_deals import (show_deals_list, format_deal_details, parse_admin_page, parse_admin_rental_id,
                                       parse_admin_rental_id_text, parse_dispute_target, parse_resolve_target_callback)

from states.admin import AdminStates
from keyboards.admin_kb import get_admin_deal_details_keyboard, get_admin_dispute_target_keyboard
from utils.functions import send_or_edit

admin_deals_router = Router()

DEALS_PREFIX = "admin:deals"
DEALS_PAGE_PREFIX = "admin:deals:page:"
DEALS_VIEW_PREFIX = "admin:deals:view:"
DEALS_BY_ID_PREFIX = "admin:deals:by_id"
DEALS_CANCEL_PREFIX = "admin:deals:cancel:"
DEALS_RESOLVE_PREFIX = "admin:deals:resolve:"
DEALS_RESOLVE_TARGET_PREFIX = "admin:deals:resolve_target:"

# ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
@admin_deals_router.callback_query(F.data == DEALS_PREFIX)
async def admin_deals_list(callback: CallbackQuery, admin_rental_service: AdminRentalService) -> None:
    """Список последних сделок (страница 1)"""
    await callback.answer()

    #await state.clear()
    await show_deals_list(callback, admin_rental_service, page=1)


@admin_deals_router.callback_query(F.data.startswith(DEALS_PAGE_PREFIX))
async def admin_deals_page(callback: CallbackQuery, admin_rental_service: AdminRentalService) -> None:
    """Пагинация списка сделок"""
    await callback.answer()

    page = parse_admin_page(callback.data)
    await show_deals_list(callback, admin_rental_service, page=page)


@admin_deals_router.callback_query(F.data.startswith(DEALS_VIEW_PREFIX))
async def admin_deals_view(callback: CallbackQuery, admin_rental_service: AdminRentalService) -> None:
    """Карточка конкретной сделки"""
    await callback.answer()

    rental_id = parse_admin_rental_id(callback.data)
    if rental_id is None:
        #await callback.answer("Некорректный ID", show_alert=True)
        return

    details = await admin_rental_service.get_details(rental_id)
    if not details:
        await send_or_edit(callback, f"❌ Сделка #{rental_id} не найдена.", None)
        return

    await send_or_edit(
        callback,
        format_deal_details(details),
        get_admin_deal_details_keyboard(rental_id=rental_id, status=details.rental.status)
    )

# ─────────────────────────────────────────── 🔎 Открыть сделку по ID ──────────────────────────────────────────────────
@admin_deals_router.callback_query(F.data == DEALS_BY_ID_PREFIX)
async def admin_deals_open_by_id(callback: CallbackQuery, state: FSMContext) -> None:
    """Просим админа ввести ID сделки"""
    await callback.answer()

    await state.set_state(AdminStates.waiting_rental_id)
    await send_or_edit(callback, "Введите ID сделки (число):", None)

@admin_deals_router.message(AdminStates.waiting_rental_id)
async def admin_deals_process_id(message: Message, state: FSMContext, admin_rental_service: AdminRentalService) -> None:
    """Обработка введенного ID сделки"""

    rental_id = parse_admin_rental_id_text(message.text)
    if rental_id is None:
        await message.answer("❌ Нужно число. Введите ID сделки:")
        return

    await state.clear()

    details = await admin_rental_service.get_details(rental_id)
    if not details:
        await message.answer(f"❌ Сделка #{rental_id} не найдена.")
        return

    await send_or_edit(
        message,
        format_deal_details(details),
        get_admin_deal_details_keyboard(rental_id=rental_id, status=details.rental.status)
    )


# ──────────────────────────────────────────────── 🚫 Отменить сделку ──────────────────────────────────────────────────
@admin_deals_router.callback_query(F.data.startswith(DEALS_CANCEL_PREFIX))
async def admin_deals_cancel_ask(callback: CallbackQuery, state: FSMContext) -> None:
    """Запрос причины отмены"""
    await callback.answer()

    rental_id = parse_admin_rental_id(callback.data)
    if rental_id is None:
        #await callback.answer("Некорректный ID", show_alert=True)
        return

    await state.set_state(AdminStates.waiting_cancel_reason)
    await state.update_data(rental_id=rental_id)

    await send_or_edit(callback, f"🚫 Укажите причину отмены сделки #{rental_id}:", None)

@admin_deals_router.message(AdminStates.waiting_cancel_reason)
async def admin_deals_cancel_apply(message: Message,state: FSMContext, admin_rental_service: AdminRentalService) -> None:
    """Применить отмену сделки с причиной"""
    data = await state.get_data()

    rental_id = data.get("rental_id")
    if rental_id is None:
        await state.clear()
        await send_or_edit(message, "❌ Не удалось определить сделку. Повторите попытку.", None)
        return
    rental_id = int(rental_id)

    reason = (message.text or "").strip()
    if not reason:
        await message.answer("❌ Причина не может быть пустой. Введите текст причины:")
        return

    await state.clear()

    ok = await admin_rental_service.admin_cancel_rental(rental_id=rental_id, admin_tg_id=message.from_user.id, reason=reason)
    if not ok:
        await message.answer("❌ Нельзя отменить эту сделку (возможно, уже завершена).")
        return

    details = await admin_rental_service.get_details(rental_id)
    if not details:
        await send_or_edit(message, f"❌ Сделка #{rental_id} не найдена.", None)
        return

    await send_or_edit(
        message,
        "✅ Отменено.\n\n" + format_deal_details(details),
        get_admin_deal_details_keyboard(rental_id=rental_id, status=details.rental.status)
    )


# ──────────────────────────────────────────────── ✅ Закрыть спор ─────────────────────────────────────────────────────
@admin_deals_router.callback_query(F.data.startswith(DEALS_RESOLVE_PREFIX))
async def admin_deals_resolve_ask(callback: CallbackQuery, state: FSMContext) -> None:
    """Запрос текста решения по спору"""
    await callback.answer()

    rental_id = parse_admin_rental_id(callback.data)
    if rental_id is None:
        #await callback.answer("Некорректный ID", show_alert=True)
        return

    await state.set_state(AdminStates.waiting_dispute_resolution)
    await state.update_data(rental_id=rental_id)

    await send_or_edit(callback, f"✅ Введите решение по спору сделки #{rental_id} (кратко):", None)


@admin_deals_router.message(AdminStates.waiting_dispute_resolution)
async def admin_deals_resolve_collect_resolution(message: Message, state: FSMContext) -> None:
    """Сохранить текст решения по спору и запросить итоговый статус"""
    data = await state.get_data()

    rental_id = data.get("rental_id")
    if rental_id is None:
        await state.clear()
        await send_or_edit(message, "❌ Не удалось определить сделку. Повторите попытку.", None)
        return
    rental_id = int(rental_id)

    resolution = (message.text or "").strip()
    if not resolution:
        await message.answer("❌ Решение не может быть пустым. Введите текст:")
        return

    await state.set_state(AdminStates.waiting_dispute_target)
    await state.update_data(resolution=resolution)

    await send_or_edit(
        message,
        f"Выберите исход закрытия спора по сделке #{rental_id}.\n\n 📝 Решение:\n{resolution}",
        get_admin_dispute_target_keyboard(rental_id)
    )

# ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
@admin_deals_router.callback_query(F.data.startswith(DEALS_RESOLVE_TARGET_PREFIX))
async def admin_deals_resolve_apply_target(callback: CallbackQuery, state: FSMContext, admin_rental_service: AdminRentalService) -> None:
    """Закрыть спор с выбранным итоговым статусом"""
    payload = parse_resolve_target_callback(callback.data)
    if payload is None:
        await callback.answer("Некорректные данные", show_alert=True)
        return

    rental_id, target = payload

    data = await state.get_data()

    resolution = (data.get("resolution") or "").strip()
    if not resolution:
        await callback.answer("Сначала введите текст решения.", show_alert=True)
        return

    target_status = parse_dispute_target(target)
    if target_status is None:
        await callback.answer("Некорректный исход", show_alert=True)
        return

    ok = await admin_rental_service.admin_resolve_dispute(
        rental_id=rental_id,
        admin_tg_id=callback.from_user.id,
        resolution=resolution,
        target_status=target_status,
    )

    await state.clear()

    if not ok:
        await callback.answer("Нельзя закрыть спор (проверь статус/сделку).", show_alert=True)
        return

    details = await admin_rental_service.get_details(rental_id)
    if not details:
        await callback.answer()
        await send_or_edit(callback, f"✅ Спор закрыт. Сделка #{rental_id}.", None)
        return

    await send_or_edit(
        callback,
        "✅ Спор закрыт.\n\n" + format_deal_details(details),
        get_admin_deal_details_keyboard(rental_id=rental_id, status=details.rental.status)
    )

    await callback.answer()