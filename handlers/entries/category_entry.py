from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from services.category_service import CategoryService
from keyboards.category_kb import build_category_keyboard
from utils.functions import send_reply
from utils.errors import ServiceError
from utils.callbacks import (CAT_CB_PREFIX,  SEARCH_CITY_CB, SEARCH_FILTERS_CB, BACK_TO_MENU_CB)

# Функцию можно дергать как - reply-menu кнопку / callback “назад” / админка
async def show_categories(event: Message | CallbackQuery, category_service: CategoryService) -> None: #state: FSMContext,
    """Показывает список категорий для выбора. Сценарий поиска («🔍 Арендовать»)"""

    if isinstance(event, CallbackQuery):
        await event.answer()

    # Получаем категории
    try:
        categories = await category_service.list_main_categories()
    except ServiceError: # Бизнес-проблема: даём понятный UX-ответ
        await send_reply(event, "⚠️ Не удалось загрузить категории. Попробуйте позже.")
        return

    categories = categories or []

    keyboard = build_categories_screen_keyboard(categories)
    message_text = "🔍 <b>Арендовать</b>\n\nВыберите категорию:"
    await send_reply(event, message_text, markup=keyboard)


# ─────────────────────────────────────────────────item_helpers──────────────────────────────────────────────────────────────
def build_categories_screen_keyboard(categories) -> InlineKeyboardMarkup:
    return build_category_keyboard(
        categories,
        prefix=CAT_CB_PREFIX,
        extra_buttons=[
            [InlineKeyboardButton(text="🏙️ Поиск по городу", callback_data=SEARCH_CITY_CB)],
            [InlineKeyboardButton(text="⚙️ Фильтры", callback_data=SEARCH_FILTERS_CB)],
            [InlineKeyboardButton(text="🔙 Назад в меню", callback_data=BACK_TO_MENU_CB)]
        ]
    )