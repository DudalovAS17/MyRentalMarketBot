from aiogram.types import Message, CallbackQuery

from services.category_service import CategoryService
from handlers.entries.entry_helper import build_categories_screen_keyboard
from utils.functions import send_reply
from utils.errors import ServiceError


async def show_categories(event: Message | CallbackQuery, category_service: CategoryService) -> None:
    """Показывает список категорий для выбора"""

    if isinstance(event, CallbackQuery):
        await event.answer()

    try:
        categories = await category_service.list_main_categories()
    except ServiceError:
        await send_reply(event, "⚠️ Не удалось загрузить категории. Попробуйте позже.")
        return

    await send_reply(
        event,
        "🔍 <b>Арендовать</b>\n\nВыберите категорию:",
        markup=build_categories_screen_keyboard(categories)
    )