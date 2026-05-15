from aiogram import F
from aiogram.types import CallbackQuery

from .router import rental_router
from .details import render_rental_details
from .rental_helpers.validate import get_rental_id_or_alert
from services.rental_service import RentalService

from schemas.user import UserOut
from utils.errors import ServiceError


# ──────────────────────────────────────────── main-function ───────────────────────────────────────────────────────────
async def _run_rental_action(
        *,
        callback: CallbackQuery,
        rental_service: RentalService,
        user: UserOut,
        rental_id: int,
        service_call, # : Callable[[], Awaitable[bool]]
        ok_text: str,
        fail_text: str
) -> None:
    """Выполнить service-action по сделке и обновить экран деталей"""

    # Вызов бизнес-логики
    try:
        ok = await service_call()
    except ServiceError:
        await callback.answer("Ошибка. Попробуйте позже.", show_alert=True)
        return

    if not ok:
        await callback.answer(fail_text, show_alert=True)
        await render_rental_details(callback, rental_service, user, rental_id)
        return

    # Успешный сценарий
    await callback.answer(ok_text)

    # Перерисовка после успеха
    await render_rental_details(callback, rental_service, user, rental_id)

# ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
@rental_router.callback_query(F.data.startswith("rental_action:confirm:"))
async def rental_confirm(callback: CallbackQuery, rental_service: RentalService, user) -> None:
    """Кнопка владельца “Подтвердить” (REQUESTED → CONFIRMED)"""

    rental_id = await get_rental_id_or_alert(callback)
    if rental_id is None:
        return

    await _run_rental_action(
        callback=callback,
        rental_service=rental_service,
        user=user,
        rental_id=rental_id,
        service_call=lambda: rental_service.confirm_requested(rental_id=rental_id, owner_id=user.id),
        ok_text="Подтверждено",
        fail_text="Не удалось подтвердить (статус изменился или нет прав)."
    )

# Владелец отклонил запрос аренды
@rental_router.callback_query(F.data.startswith("rental_action:rejected_by_owner:"))
async def rental_reject_by_owner(callback: CallbackQuery, rental_service: RentalService, user) -> None:
    """Кнопка владельца “❌ Отклонить” (REQUESTED → REJECTED_BY_OWNER)"""

    rental_id = await get_rental_id_or_alert(callback)
    if rental_id is None:
        return

    await _run_rental_action(
        callback=callback,
        rental_service=rental_service,
        user=user,
        rental_id=rental_id,
        service_call=lambda: rental_service.reject_requested_by_owner(rental_id=rental_id, owner_id=user.id),
        ok_text="Отклонено",
        fail_text="Не удалось отклонить (статус изменился или нет прав)."
    )

# Арендатор отклонил свой запрос аренды
@rental_router.callback_query(F.data.startswith("rental_action:rejected_by_renter:"))
async def rental_reject_by_renter(callback: CallbackQuery, rental_service: RentalService, user) -> None:
    """Кнопка арендатора “❌ Отклонить” (REQUESTED → REJECTED_BY_RENTER)"""

    rental_id = await get_rental_id_or_alert(callback)
    if rental_id is None:
        return

    await _run_rental_action(
        callback=callback,
        rental_service=rental_service,
        user=user,
        rental_id=rental_id,
        service_call=lambda: rental_service.reject_requested_by_renter(rental_id=rental_id, renter_id=user.id),
        ok_text="Запрос отменён",
        fail_text="Не удалось отменить (статус изменился или нет прав)."
    )

# Владелец отменяет подтвержденную аренду
@rental_router.callback_query(F.data.startswith("rental_action:cancelled_confirmed_by_owner:"))
async def rental_cancel_confirmed_by_owner(callback: CallbackQuery, rental_service: RentalService, user) -> None:
    """Отменить подтверждённую аренду владельцем"""
    rental_id = await get_rental_id_or_alert(callback)
    if rental_id is None:
        return

    await _run_rental_action(
        callback=callback,
        rental_service=rental_service,
        user=user,
        rental_id=rental_id,
        service_call=lambda: rental_service.cancel_confirmed_by_owner(rental_id=rental_id, owner_id=user.id),
        ok_text="Аренда отменена владельцем",
        fail_text="Не удалось отменить (статус изменился или нет прав)."
    )

# Арендатор отменяет подтвержденную аренду
@rental_router.callback_query(F.data.startswith("rental_action:cancelled_confirmed_by_renter:"))
async def rental_cancel_confirmed_by_renter(callback: CallbackQuery, rental_service: RentalService, user) -> None:
    """Отменить подтверждённую аренду арендатором"""
    rental_id = await get_rental_id_or_alert(callback)
    if rental_id is None:
        return

    await _run_rental_action(
        callback=callback,
        rental_service=rental_service,
        user=user,
        rental_id=rental_id,
        service_call=lambda: rental_service.cancel_confirmed_by_renter(rental_id=rental_id, renter_id=user.id),
        ok_text="Аренда отменена арендатором",
        fail_text="Не удалось отменить (статус изменился или нет прав)."
    )

# Владелец отменяет активную аренду
@rental_router.callback_query(F.data.startswith("rental_action:cancelled_by_owner:"))
async def rental_cancel_active_by_owner(callback: CallbackQuery, rental_service: RentalService, user) -> None:
    """Владелец отменяет активную аренду"""
    rental_id = await get_rental_id_or_alert(callback)
    if rental_id is None:
        return

    await _run_rental_action(
        callback=callback,
        rental_service=rental_service,
        user=user,
        rental_id=rental_id,
        service_call=lambda: rental_service.cancel_active_by_owner(rental_id=rental_id, owner_id=user.id),
        ok_text="Активная аренда отменена владельцем",
        fail_text="Не удалось отменить (статус изменился или нет прав)."
    )

# Арендатор отменяет активную аренду
@rental_router.callback_query(F.data.startswith("rental_action:cancelled_by_renter:"))
async def rental_cancel_active_by_renter(callback: CallbackQuery, rental_service: RentalService, user) -> None:
    """Арендатор отменяет активную аренду"""
    rental_id = await get_rental_id_or_alert(callback)
    if rental_id is None:
        return

    await _run_rental_action(
        callback=callback,
        rental_service=rental_service,
        user=user,
        rental_id=rental_id,
        service_call=lambda: rental_service.cancel_active_by_renter(rental_id=rental_id, renter_id=user.id),
        ok_text="Активная аренда отменена арендатором",
        fail_text="Не удалось отменить (статус изменился или нет прав)."
    )

# ─────────────────────────────────────── это не статусы, а булевый флаг ───────────────────────────────────────────────
# “Передал вещь” (owner)
@rental_router.callback_query(F.data.startswith("rental_action:handover_owner:"))
async def rental_handover_owner(callback: CallbackQuery, rental_service: RentalService, user) -> None:
    """Зафиксировать передачу вещи владельцем"""
    rental_id = await get_rental_id_or_alert(callback)
    if rental_id is None:
        return

    await _run_rental_action(
        callback=callback,
        rental_service=rental_service,
        user=user,
        rental_id=rental_id,
        service_call=lambda: rental_service.confirm_handover_by_owner(rental_id=rental_id, owner_id=user.id),
        ok_text="Отмечено: вещь передана",
        fail_text="Не удалось отметить (статус изменился / нет прав / уже отмечено)."
    )

# “Получил вещь” (renter)
@rental_router.callback_query(F.data.startswith("rental_action:receive_renter:"))
async def rental_receive_renter(callback: CallbackQuery, rental_service: RentalService, user) -> None:
    """Зафиксировать получение вещи арендатором"""
    rental_id = await get_rental_id_or_alert(callback)
    if rental_id is None:
        return

    await _run_rental_action(
        callback=callback,
        rental_service=rental_service,
        user=user,
        rental_id=rental_id,
        service_call=lambda: rental_service.confirm_receive_by_renter(rental_id=rental_id, renter_id=user.id),
        ok_text="Отмечено: вещь получена",
        fail_text="Не удалось отметить (статус изменился / нет прав / уже отмечено)."
    )

# ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
# ✅ Завершить (owner)
@rental_router.callback_query(F.data.startswith("rental_action:complete:"))
async def rental_complete(callback: CallbackQuery, rental_service: RentalService, user) -> None:
    """Завершить активную аренду владельцем"""
    rental_id = await get_rental_id_or_alert(callback)
    if rental_id is None:
        return

    await _run_rental_action(
        callback=callback,
        rental_service=rental_service,
        user=user,
        rental_id=rental_id,
        service_call=lambda: rental_service.complete_active(rental_id=rental_id, owner_id=user.id),
        ok_text="Аренда завершена",
        fail_text="Не удалось завершить (статус изменился или нет прав)"
    )

# ⚠️ Открыть спор (owner/renter)
@rental_router.callback_query(F.data.startswith("rental_action:dispute:"))
async def rental_dispute(callback: CallbackQuery, rental_service: RentalService, user) -> None:
    """Открыть спор по сделке"""
    rental_id = await get_rental_id_or_alert(callback)
    if rental_id is None:
        return

    await _run_rental_action(
        callback=callback,
        rental_service=rental_service,
        user=user,
        rental_id=rental_id,
        service_call=lambda: rental_service.open_dispute(rental_id=rental_id, actor_id=user.id),
        ok_text="Спор открыт",
        fail_text="Не удалось открыть спор (статус изменился или нет прав)"
    )