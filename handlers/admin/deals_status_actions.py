from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from collections.abc import Awaitable, Callable

from services.admin_rental_service import AdminRentalService
from services.notif_service import NotificationService
from .admin_helpers.show import show_deal_card
from .admin_helpers.parse import parse_admin_rental_id

from states.admin import AdminStates
from utils.functions import send_or_edit
from utils.callbacks import (DEALS_PROGRESS_PREFIX, DEALS_CONFIRM_PREFIX, DEALS_REJECT_PREFIX, DEALS_COMPLETE_PREFIX,
                             DEALS_CANCEL_PREFIX, DEALS_COMMENT_PREFIX)

admin_status_actions_router = Router()

# *****

AdminRentalAction = Callable[[int], Awaitable[object | None]]

# REQUESTED → IN_PROGRESS
@admin_status_actions_router.callback_query(F.data.startswith(DEALS_PROGRESS_PREFIX))
async def admin_deals_take_in_progress(
        callback: CallbackQuery,
        admin_rental_service: AdminRentalService,
        notification_service: NotificationService
) -> None:
    """Взять заявку в работу: REQUESTED → IN_PROGRESS."""
    await apply_admin_deal_action(
        callback,
        admin_rental_service,
        notification_service,
        action_name="Заявка взята в работу",
        service_call=lambda rental_id: admin_rental_service.take_in_progress(
            rental_id=rental_id,
            admin_tg_id=callback.from_user.id,
        ),
    )

# REQUESTED/IN_PROGRESS → CONFIRMED
@admin_status_actions_router.callback_query(F.data.startswith(DEALS_CONFIRM_PREFIX))
async def admin_deals_confirm(
        callback: CallbackQuery,
        admin_rental_service: AdminRentalService,
        notification_service: NotificationService
) -> None:
    """Подтвердить заявку: REQUESTED/IN_PROGRESS → CONFIRMED."""
    await apply_admin_deal_action(
        callback,
        admin_rental_service,
        notification_service,
        action_name="Заявка подтверждена",
        service_call=lambda rental_id: admin_rental_service.confirm_rental(
            rental_id=rental_id,
            admin_tg_id=callback.from_user.id,
        ),
    )

# CONFIRMED → COMPLETED
@admin_status_actions_router.callback_query(F.data.startswith(DEALS_COMPLETE_PREFIX))
async def admin_deals_complete(
        callback: CallbackQuery,
        admin_rental_service: AdminRentalService,
        notification_service: NotificationService
) -> None:
    """Завершить подтверждённую аренду: CONFIRMED → COMPLETED."""
    await apply_admin_deal_action(
        callback,
        admin_rental_service,
        notification_service,
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
async def admin_deals_reject_apply(
        message: Message,
        state: FSMContext,
        admin_rental_service: AdminRentalService,
        notification_service: NotificationService
) -> None:
    """Отклонить заявку с причиной: REQUESTED/IN_PROGRESS → REJECTED."""
    result = await get_reasoned_action_payload(message, state)  # тут состояние обнуляется
    if result is None:
        return
    rental_id, reason = result

    ok = await admin_rental_service.reject_rental(rental_id=rental_id, admin_tg_id=message.from_user.id, reason=reason)
    if not ok:
        await message.answer("❌ Нельзя отклонить эту заявку (возможно, статус уже изменился).")
        return

    await notify_user_about_admin_rental_status(admin_rental_service, notification_service, rental_id)

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
async def admin_deals_cancel_apply(
        message: Message,
        state: FSMContext,
        admin_rental_service: AdminRentalService,
        notification_service: NotificationService
) -> None:
    """FSM: Отменить подтверждённую заявку с причиной"""
    result = await get_reasoned_action_payload(message, state) # тут состояние обнуляется
    if result is None:
        return
    rental_id, reason = result

    ok = await admin_rental_service.admin_cancel_rental(rental_id=rental_id, admin_tg_id=message.from_user.id, reason=reason)
    if not ok:
        await message.answer("❌ Нельзя отменить подтверждённую заявку (возможно, статус уже изменился).")
        return

    await notify_user_about_admin_rental_status(admin_rental_service, notification_service, rental_id)

    await show_deal_card(message, admin_rental_service, rental_id) # , prefix_text="✅ Заявка отклонена.\n\n")

# ─────────── FSM: 📝 Комментарий менеджера ──────────────
@admin_status_actions_router.callback_query(F.data.startswith(DEALS_COMMENT_PREFIX))
async def admin_deals_comment_ask(callback: CallbackQuery, state: FSMContext) -> None:
    """FSM: Запросить внутренний комментарий менеджера."""
    rental_id = parse_admin_rental_id(callback.data)
    if rental_id is None:
        await callback.answer("Некорректный ID заявки", show_alert=True)
        return

    await callback.answer()
    await state.set_state(AdminStates.waiting_rental_manager_comment)
    await state.update_data(rental_id=rental_id)
    await send_or_edit(callback, f"📝 Введите комментарий менеджера для заявки #{rental_id}:", None)


@admin_status_actions_router.message(AdminStates.waiting_rental_manager_comment)
async def admin_deals_comment_apply(
        message: Message,
        state: FSMContext,
        admin_rental_service: AdminRentalService,
) -> None:
    """Сохранить внутренний комментарий менеджера."""
    result = await get_reasoned_action_payload(message, state)
    if result is None:
        return
    rental_id, comment = result

    updated = await admin_rental_service.update_manager_comment(
        rental_id=rental_id,
        admin_tg_id=message.from_user.id,
        manager_comment=comment,
    )
    if not updated:
        await message.answer("❌ Не удалось сохранить комментарий менеджера.")
        return

    await show_deal_card(message, admin_rental_service, rental_id, "✅ Комментарий менеджера сохранён.\n\n")


# ─────────────────────────────────────────────────── helpers ──────────────────────────────────────────────────────────
async def apply_admin_deal_action(
    callback: CallbackQuery,
    admin_rental_service: AdminRentalService,
    notification_service: NotificationService,
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

    await notify_user_about_admin_rental_status(admin_rental_service, notification_service, rental_id)

    await callback.answer(action_name)
    await show_deal_card(callback, admin_rental_service, rental_id, f"✅ {action_name}.\n\n")


async def notify_user_about_admin_rental_status(admin_rental_service: AdminRentalService, notification_service: NotificationService, rental_id: int) -> None:
    """Загрузить заявку и безопасно уведомить клиента о текущем статусе."""
    details = await admin_rental_service.get_details(rental_id)
    if details is None:
        return
    await notification_service.notify_user_rental_status_changed(details.user.telegram_id, details)


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