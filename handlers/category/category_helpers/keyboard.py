from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from keyboards.category_kb import build_category_keyboard
from utils.callbacks import SUBCAT_CB_PREFIX, ALL_CATEGORY_CB, BACK_TO_CAT, ITEM_DETAILS_CB

def build_subcategories_keyboard(subcategories, category) -> InlineKeyboardMarkup:
    """Собрать клавиатуру подкатегорий выбранной категории. Идея: Добавляем кнопки для каждой подкатегории"""
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
    )

def build_back_to_item_details_keyboard(item_id: int) -> InlineKeyboardMarkup:
    """Собрать клавиатуру возврата к деталям объявления"""
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(
            text="🔙 Назад (к деталям объявления)",
            callback_data=f"{ITEM_DETAILS_CB}{item_id}"
        )]]
    )


# карусель
def build_items_carousel_keyboard(
    *,
    current_item_id: int,
    subcategory_id: int,
    parent_category_id: int | None,
    current_index: int,
    total_items: int,
    nav_cb_prefix: str,
    item_details_cb_prefix: str,
    subcat_cb_prefix: str,
    cat_cb_prefix: str,
) -> InlineKeyboardMarkup:
    """Клавиатура для карточной навигации по объявлениям в подкатегории."""

    buttons: list[list[InlineKeyboardButton]] = []

    if total_items > 1:
        prev_index = (current_index - 1) % total_items
        next_index = (current_index + 1) % total_items
        buttons.append([
            InlineKeyboardButton(text="⬅️", callback_data=f"{nav_cb_prefix}{subcategory_id}:{prev_index}"),
            InlineKeyboardButton(text=f"{current_index + 1} / {total_items}", callback_data="noop"),
            InlineKeyboardButton(text="➡️", callback_data=f"{nav_cb_prefix}{subcategory_id}:{next_index}"),
        ])

    buttons.append([InlineKeyboardButton(text="🔍 Подробнее", callback_data=f"{item_details_cb_prefix}{current_item_id}")])

    if parent_category_id:
        buttons.append([InlineKeyboardButton(text="🔙 Назад (к подкатегориям)", callback_data=f"{cat_cb_prefix}{parent_category_id}")])
    else:
        buttons.append([InlineKeyboardButton(text="🔙 Назад (к подкатегориям)", callback_data=f"{subcat_cb_prefix}{subcategory_id}")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)