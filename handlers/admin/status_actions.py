from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from collections.abc import Awaitable, Callable

from services.admin_rental_service import AdminRentalService
from .admin_helpers.show import show_deal_card
from .admin_helpers.parse import parse_admin_rental_id

from states.admin import AdminStates
from utils.functions import send_or_edit

admin_status_actions_router = Router()

DEALS_PROGRESS_PREFIX = "admin:deals:progress:"
DEALS_CONFIRM_PREFIX = "admin:deals:confirm:"
DEALS_REJECT_PREFIX = "admin:deals:reject:"
DEALS_COMPLETE_PREFIX = "admin:deals:complete:"
DEALS_CANCEL_PREFIX = "admin:deals:cancel:"

AdminRentalAction = Callable[[int], Awaitable[object | None]]

# REQUESTED → IN_PROGRESS
@admin_status_actions_router.callback_query(F.data.startswith(DEALS_PROGRESS_PREFIX))
async def admin_deals_take_in_progress(callback: CallbackQuery, admin_rental_service: AdminRentalService) -> None:
    """Взять заявку в работу: REQUESTED → IN_PROGRESS."""
    await apply_admin_deal_action(
        callback,
        admin_rental_service,
        action_name="Заявка взята в работу",
        service_call=lambda rental_id: admin_rental_service.take_in_progress(
            rental_id=rental_id,
            admin_tg_id=callback.from_user.id,
        ),
    )

# REQUESTED/IN_PROGRESS → CONFIRMED
@admin_status_actions_router.callback_query(F.data.startswith(DEALS_CONFIRM_PREFIX))
async def admin_deals_confirm(callback: CallbackQuery, admin_rental_service: AdminRentalService) -> None:
    """Подтвердить заявку: REQUESTED/IN_PROGRESS → CONFIRMED."""
    await apply_admin_deal_action(
        callback,
        admin_rental_service,
        action_name="Заявка подтверждена",
        service_call=lambda rental_id: admin_rental_service.confirm_rental(
            rental_id=rental_id,
            admin_tg_id=callback.from_user.id,
        ),
    )

# CONFIRMED → COMPLETED
@admin_status_actions_router.callback_query(F.data.startswith(DEALS_COMPLETE_PREFIX))
async def admin_deals_complete(callback: CallbackQuery, admin_rental_service: AdminRentalService) -> None:
    """Завершить подтверждённую аренду: CONFIRMED → COMPLETED."""
    await apply_admin_deal_action(
        callback,
        admin_rental_service,
        action_name="Аренда завершена",
        service_call=lambda rental_id: admin_rental_service.complete_rental(
            rental_id=rental_id,
            admin_tg_id=callback.from_user.id,
        ),
    )

# ─────────── FSM: 🚫 Отклонение заявки ──────────────
@admin_status_actions_router.callback_query(F.data.startswith(DEALS_REJECT_PREFIX))
async def admin_deals_reject_ask(callback: CallbackQuery, state: FSMContext) -> None:
    """FSM: Запросить причину отклонения заявки."""
    rental_id = parse_admin_rental_id(callback.data)
    if rental_id is None:
        await callback.answer("Некорректный ID заявки", show_alert=True)
        return

    await callback.answer()
    await state.set_state(AdminStates.waiting_rental_reject_reason)
    await state.update_data(rental_id=rental_id)
    await send_or_edit(callback,f"❌ Укажите причину отклонения заявки #{rental_id}:", None)

# REQUESTED/IN_PROGRESS → REJECTED
@admin_status_actions_router.message(AdminStates.waiting_rental_reject_reason)
async def admin_deals_reject_apply(message: Message, state: FSMContext, admin_rental_service: AdminRentalService) -> None:
    """Отклонить заявку с причиной: REQUESTED/IN_PROGRESS → REJECTED."""
    result = get_reasoned_action_payload(message, state)  # тут состояние обнуляется
    if result is None:
        return
    rental_id, reason = result

    ok = await admin_rental_service.reject_rental(rental_id=rental_id, admin_tg_id=message.from_user.id, reason=reason)
    if not ok:
        await message.answer("❌ Нельзя отклонить эту заявку (возможно, статус уже изменился).")
        return

    await show_deal_card(message, admin_rental_service, rental_id) # , prefix_text="✅ Заявка отклонена.\n\n")

# ─────────── FSM: 🚫 Отменить аренду ──────────────
@admin_status_actions_router.callback_query(F.data.startswith(DEALS_CANCEL_PREFIX))
async def admin_deals_cancel_ask(callback: CallbackQuery, state: FSMContext) -> None:
    """FSM: Запросить причину отмены подтверждённой компанией заявки."""
    rental_id = parse_admin_rental_id(callback.data)
    if rental_id is None:
        await callback.answer("Некорректный ID заявки", show_alert=True)
        return

    await callback.answer()
    await state.set_state(AdminStates.waiting_rental_cancel_reason)
    await state.update_data(rental_id=rental_id)
    await send_or_edit(callback, f"🚫 Укажите причину отмены аренды #{rental_id}:", None)

# CONFIRMED → CANCELLED_BY_ADMIN
@admin_status_actions_router.message(AdminStates.waiting_rental_cancel_reason)
async def admin_deals_cancel_apply(message: Message,state: FSMContext, admin_rental_service: AdminRentalService) -> None:
    """FSM: Отменить подтверждённую заявку с причиной"""
    result = get_reasoned_action_payload(message, state) # тут состояние обнуляется
    if result is None:
        return
    rental_id, reason = result

    ok = await admin_rental_service.admin_cancel_rental(rental_id=rental_id, admin_tg_id=message.from_user.id, reason=reason)
    if not ok:
        await message.answer("❌ Нельзя отменить подтверждённую заявку (возможно, статус уже изменился).")
        return

    await show_deal_card(message, admin_rental_service, rental_id) # , prefix_text="✅ Заявка отклонена.\n\n")


# ─────────────────────────────────────────────────── helpers ──────────────────────────────────────────────────────────
async def apply_admin_deal_action(
    callback: CallbackQuery,
    admin_rental_service: AdminRentalService,
    *,
    action_name: str,
    service_call: AdminRentalAction,
) -> None:
    """Выполнить админское действие над заявкой и перерисовать карточку."""
    rental_id = parse_admin_rental_id(callback.data)
    if rental_id is None:
        await callback.answer("Некорректный ID заявки", show_alert=True)
        return

    updated = await service_call(rental_id)
    if not updated:
        await callback.answer(f"Не удалось выполнить действие: {action_name}.", show_alert=True)
        #await show_deal_card(callback, admin_rental_service, rental_id)
        return

    await callback.answer(action_name)
    await show_deal_card(callback, admin_rental_service, rental_id, f"✅ {action_name}.\n\n")

async def get_reasoned_action_payload(message: Message, state: FSMContext) -> tuple[int, str] | None:
    """Достать rental_id и обязательную причину из FSM/message. И чистит состояние!"""
    data = await state.get_data()

    rental_id_raw = data.get("rental_id")
    if rental_id_raw is None:
        await state.clear()
        await send_or_edit(message, "❌ Не удалось определить заявку. Повторите попытку.", None)
        return None

    try:
        rental_id = int(rental_id_raw)
    except (TypeError, ValueError):
        await state.clear()
        await send_or_edit(message, "❌ Некорректный ID заявки. Повторите попытку.", None)
        return None

    reason = (message.text or "").strip()
    if not reason:
        await message.answer("❌ Причина не может быть пустой. Введите текст причины:")
        return None

    await state.clear()
    return rental_id, reason


# ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
""" Удалено:

# 🚫 Отменить сделку
# admin_deals_cancel_ask - Запрос причины отмены (DEALS_CANCEL_PREFIX)

# AdminStates.waiting_rental_cancel_reason) # .waiting_cancel_reason
# admin_deals_cancel_apply - Применить отмену сделки с причиной

# ✅ Закрыть спор
# admin_deals_resolve_ask - Запрос текста решения по спору (DEALS_RESOLVE_PREFIX)

# AdminStates.waiting_rental_resolution / waiting_dispute_resolution
# admin_deals_resolve_collect_resolution - Сохранить текст решения по спору и запросить итоговый статус

# admin_deals_resolve_apply_target - Закрыть спор с выбранным итоговым статусом (DEALS_RESOLVE_TARGET_PREFIX)
"""