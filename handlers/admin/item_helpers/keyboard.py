from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from keyboards.common import build_category_keyboard
from utils.callbacks import (MY_ITEMS_PREFIX, CAT_FI_PREFIX, PUBLISH_ITEM_CB, CANCEL_ITEM_CB,
                             SUBCAT_FI_PREFIX, BACK_TO_MENU_CB, BACK_TO_CAT)

# ─────────────────────────────────────────────────show─────────────────────────────────────────────────────────────────
def build_back_to_my_items_keyboard() -> InlineKeyboardMarkup:
    """Собрать клавиатуру возврата к списку моих товаров"""
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(
            text="🔙 Назад (к моим товарам)",
            callback_data=MY_ITEMS_PREFIX
        )]]
    )

# ─────────────────────────────────────────────────flow_create──────────────────────────────────────────────────────────
def build_create_item_categories_keyboard(categories) -> InlineKeyboardMarkup:
    """Собрать клавиатуру выбора категории при создании товара"""
    return build_category_keyboard(
        categories,
        prefix=CAT_FI_PREFIX,
        extra_buttons=[
            [InlineKeyboardButton(text="🔙 Назад в меню", callback_data=BACK_TO_MENU_CB)]
        ],
    )

def build_create_item_subcategories_keyboard(subcategories) -> InlineKeyboardMarkup:
    """Собрать клавиатуру выбора подкатегории при создании товара"""
    return build_category_keyboard(
        subcategories,
        prefix=SUBCAT_FI_PREFIX,
        extra_buttons=[
            [InlineKeyboardButton(text="🔙 Назад (к категориям)", callback_data=BACK_TO_CAT)]
        ],
    )

def build_item_confirmation_keyboard() -> InlineKeyboardMarkup:
    """Собрать клавиатуру подтверждения создания товара"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Разместить товар", callback_data=PUBLISH_ITEM_CB)],
            [InlineKeyboardButton(text="❌ Отмена", callback_data=CANCEL_ITEM_CB)],
        ]
    )