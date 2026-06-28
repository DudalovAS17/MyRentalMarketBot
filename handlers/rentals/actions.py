from aiogram import F
from aiogram.types import CallbackQuery

from .router import rental_router
from .details import render_rental_details
from .rental_helpers.validate import get_rental_id_or_alert
from services.rental_service import RentalService
from services.notif_service import NotificationService

from schemas.user import UserOut
from utils.errors import ServiceError
from utils.callbacks import CLIENT_CANCEL_RENTAL_CB

""" Действия клиента:
- отменить заявку (до CONFIRMED) - CANCELLED_BY_CLIENT
    После перехода сделки (админом) в статус CONFIRMED - у пользователя уже нет пропадает кнопка "заявку"
- написать в поддержку (после CONFIRMED) - это уже будет в хендлере SUPPORT.
"""

# ──────────────────────────────────────────── main-function ───────────────────────────────────────────────────────────
async def run_rental_action(
        *,
        callback: CallbackQuery,
        rental_service: RentalService,
        user: UserOut,
        rental_id: int,
        service_call, # : Callable[[], Awaitable[bool]]
        ok_text: str,
        fail_text: str,
        after_success=None,
) -> None:
    """Выполнить клиентское действие с заявкой и обновить экран деталей"""

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
    if after_success is not None:
        await after_success()

    await callback.answer(ok_text)

    # Перерисовка после успеха
    await render_rental_details(callback, rental_service, user, rental_id)

# ───────────────────────────────────────────── Actions ────────────────────────────────────────────────────────────────
@rental_router.callback_query(F.data.startswith(CLIENT_CANCEL_RENTAL_CB))
async def rental_cancel_by_client(
        callback: CallbackQuery,
        rental_service: RentalService,
        notification_service: NotificationService,
        admin_ids: list[int],
        user
) -> None:
    """Кнопка “❌ Отклонить” клиента (REQUESTED → CANCELLED_BY_CLIENT)"""
    rental_id = await get_rental_id_or_alert(callback)
    if rental_id is None:
        await callback.answer("Некорректная заявка.", show_alert=True)
        return

    await run_rental_action(callback=callback, rental_service=rental_service, user=user, rental_id=rental_id,
                            service_call=lambda: rental_service.cancel_by_client(rental_id=rental_id, user_id=user.id),
                            ok_text="Запрос аренды отменён",
                            fail_text="Не удалось отменить запрос на аренду (статус изменился или нет прав).",
                            after_success=lambda: notify_client_cancelled_rental(rental_service, notification_service, admin_ids, user, rental_id=rental_id))


async def notify_client_cancelled_rental(
        rental_service: RentalService,
        notification_service: NotificationService,
        admin_ids: list[int],
        user: UserOut,
        rental_id: int
) -> None:
    """Уведомить клиента и админов после успешной отмены заявки клиентом."""
    details = await rental_service.get_rental_details(rental_id, user.id)
    if details is None:
        return

    await notification_service.notify_user_rental_cancelled(user.telegram_id, details)
    await notification_service.notify_admins_client_cancelled_rental(admin_ids, details)