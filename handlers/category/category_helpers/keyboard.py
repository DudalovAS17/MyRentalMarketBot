from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from keyboards.category_kb import build_category_keyboard
from utils.callbacks import SUBCAT_CB_PREFIX, ALL_CATEGORY_CB, BACK_TO_CAT, ITEM_DETAILS_CB

def build_subcategories_keyboard(subcategories, category) -> InlineKeyboardMarkup:
    return build_category_keyboard(
        subcategories,
        prefix=SUBCAT_CB_PREFIX,
        extra_buttons=[
            [InlineKeyboardButton(
                text=f"📋 Все в категории {category.name}",
                callback_data=f"{ALL_CATEGORY_CB}:{category.id}")],
            [InlineKeyboardButton(
                text="🔙 Назад (к категориям)",
                callback_data=BACK_TO_CAT)],
        ],
    ) # Идея: Добавляем кнопки для каждой подкатегории

def build_back_to_item_details_keyboard(item_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(
            text="🔙 Назад (к деталям объявления)",
            callback_data=f"{ITEM_DETAILS_CB}{item_id}")]])