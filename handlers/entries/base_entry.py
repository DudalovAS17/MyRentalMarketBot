from aiogram.types import CallbackQuery, Message

from keyboards.main_kb import get_main_menu_keyboard
from handlers.entries.entry_helper import build_main_menu_text
from utils.functions import send_reply


async def show_main_menu(event: Message | CallbackQuery, user) -> None:
    """Показывает главное меню"""

    await send_reply(
        event,
        build_main_menu_text(user),
        markup=get_main_menu_keyboard()
    )