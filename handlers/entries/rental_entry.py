from aiogram.types import CallbackQuery, Message

from services.rental_service import RentalService
from handlers.entries.entry_helper import build_empty_my_rentals_keyboard, build_my_rentals_keyboard

from utils.functions import send_or_edit
from utils.errors import ServiceError

async def show_my_rentals(event: Message | CallbackQuery, rental_service: RentalService, user) -> None:
    """Показывает список заявок пользователя"""

    if isinstance(event, CallbackQuery):
        await event.answer()

    try:
        rentals = await rental_service.list_rentals_by_user(user.id)
    except ServiceError:
        await send_or_edit(event, "⚠️ Не удалось загрузить список заявок. Попробуйте позже.")
        return

    if not rentals:
        await send_or_edit(
            event,
            "📭 У вас пока нет активных или завершённых заявок.",
            markup = build_empty_my_rentals_keyboard()
        )
        return

    await send_or_edit(
        event,
        "<b>📋 Ваши заявки</b>\n\n Выберите заявку, чтобы открыть детали:",
        markup=build_my_rentals_keyboard(rentals, current_user_id=user.id)
    )