from aiogram.types import Message, CallbackQuery

from services.item_service import ItemService
from handlers.item.item_helpers.texts import my_items_screen_text
from keyboards.item_kb import build_my_items_keyboard
from utils.functions import send_or_edit, send_reply
from utils.errors import ServiceError

async def show_my_items(event: Message | CallbackQuery, item_service: ItemService, user) -> None:
    """Показывает список объявлений пользователя"""

    if isinstance(event, CallbackQuery):
        await event.answer()

    try:
        items = await item_service.list_by_items_user_id(user.id)
    except ServiceError:
        await send_reply(event, "⚠️ Не удалось загрузить ваши объявления. Попробуйте позже.")
        return

    await send_or_edit(
        event,
        my_items_screen_text(count=len(items)),
        markup=build_my_items_keyboard(items)
    )