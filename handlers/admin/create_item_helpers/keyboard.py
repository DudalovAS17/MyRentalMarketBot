from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

from utils.callbacks import (CAT_FI_PREFIX, PUBLISH_ITEM_CB, CANCEL_ITEM_CB,
                             SUBCAT_FI_PREFIX, BACK_TO_MENU_CB, BACK_TO_CAT)

from keyboards.common import build_category_keyboard


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

# build_back_to_my_items_keyboard() - Собрать клавиатуру возврата к списку моих товаров
# "🔙 Назад (к моим товарам)" - MY_ITEMS_PREFIX

def get_photos_keyboard():
    return ReplyKeyboardMarkup(
        resize_keyboard=True,
        keyboard=[[KeyboardButton(text="✅ Готово")]]
            #[KeyboardButton(text="🔙 Назад")],
    )