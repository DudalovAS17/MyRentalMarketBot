from aiogram import F
from aiogram.types import CallbackQuery, Message

from .router import rental_router

from handlers.rentals.rental_helpers.rental_ui import build_rental_details_ui
from handlers.entries import show_my_rentals
from services.rental_service import RentalService

from utils.functions import send_or_edit
from utils.validators import parse_callback
from utils.errors import ServiceError
from utils.callbacks import MY_RENTALS_CB, RENTAL_DETAILS_CB #, BACK_TO_RENTALS


@rental_router.message(F.text == "📋 Мои сделки") # Мои заявки
@rental_router.callback_query(F.data == MY_RENTALS_CB)
# @rental_router.callback_query(F.data == BACK_TO_RENTALS)
async def view_my_rentals(event: Message | CallbackQuery, rental_service: RentalService, user) -> None:
    """Открыть клиентский список заявок."""
    await show_my_rentals(event, rental_service, user)

@rental_router.callback_query(F.data.startswith(RENTAL_DETAILS_CB))
async def show_rental_details(callback: CallbackQuery, rental_service: RentalService, user) -> None:
    """Открыть клиентский экран деталей конкретной аренды."""
    rental_id = parse_callback(callback.data, RENTAL_DETAILS_CB)
    if rental_id is None:
        await callback.answer("Некорректный id заявки.", show_alert=True)
        return

    await callback.answer()
    await render_rental_details(callback, rental_service, user, rental_id)

# ──────────────────────────────────────────────────── helper ──────────────────────────────────────────────────────────
async def render_rental_details(callback: CallbackQuery, rental_service: RentalService, user, rental_id: int) -> None:
    """Перерисовать клиентский экран деталей заявки."""

    try:
        details = await rental_service.get_rental_details(rental_id=rental_id, current_user_id=user.id)
    except ServiceError:
        await send_or_edit(callback, "⚠️ Не удалось загрузить детали аренды. Попробуйте позже.")
        return

    if not details:
        await send_or_edit(callback, "❌ Не удалось загрузить детали аренды или у вас нет доступа.")
        return

    text, markup = build_rental_details_ui(details)
    await send_or_edit(callback, text, markup=markup, parse_mode="HTML")