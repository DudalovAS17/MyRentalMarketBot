from collections.abc import Sequence
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from keyboards.common import build_category_keyboard
from utils.callbacks import (SUBCAT_CB_PREFIX, BACK_TO_CAT, ITEM_DETAILS_CB, RENT_ITEM_CB,
                             SHOW_ALL_PHOTOS_CB, MESSAGE_OWNER_CB, REVIEWS_CB, CAROUSEL_NAV_CB) # , ALL_CATEGORY_CB
from schemas.category import CategoryOut


"""
build_category_keyboard - показ категорий
build_subcategories_keyboard - показ подкатегорий - SUBCAT_CB_PREFIX / {ALL_CATEGORY_CB}:{category.id} / BACK_TO_CAT
build_items_carousel_keyboard - показ товаров (каруселью)
build_item_details_kb - показ деталей товара
build_back_to_item_details_keyboard - возврата к деталям товара - {ITEM_DETAILS_CB}{item_id}
"""

def build_subcategories_keyboard(subcategories: Sequence[CategoryOut], category: CategoryOut) -> InlineKeyboardMarkup:
    """Собрать клавиатуру подкатегорий выбранной категории."""
    return build_category_keyboard(
        subcategories,
        prefix=SUBCAT_CB_PREFIX,
        extra_buttons=[
            # [InlineKeyboardButton(
            #     text=f"📋 Все в категории {category.name}",
            #     callback_data=f"{ALL_CATEGORY_CB}:{category.id}")],
            [InlineKeyboardButton(
                text="🔙 Назад (к категориям)",
                callback_data=BACK_TO_CAT)],
        ],
    )


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
    """Клавиатура для карточной навигации по товарам внутри подкатегории."""

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


def build_item_details_kb(
    item_id: int,
    *,
    is_busy: bool,
    selected_subcategory_id: int | None,
    selected_item_index: int | None = None,
    end_date: str | None,
) -> InlineKeyboardMarkup:
    buttons: list[list[InlineKeyboardButton]] = []

    if is_busy:
        button_text = f"⛔ Сейчас занято (до {end_date})" if end_date else "⛔ Сейчас занято"
        buttons.append([InlineKeyboardButton(text=button_text, callback_data="noop")])
    else:
        buttons.append([InlineKeyboardButton(text="✅ Арендовать", callback_data=f"{RENT_ITEM_CB}{item_id}")])

    buttons.append([InlineKeyboardButton(text="📸 Показать все фото", callback_data=f"{SHOW_ALL_PHOTOS_CB}{item_id}")])
    buttons.append([InlineKeyboardButton(text="💬 Написать менеджеру", callback_data=f"{MESSAGE_OWNER_CB}{item_id}")])
    buttons.append([InlineKeyboardButton(text="⭐ Отзывы", callback_data=f"{REVIEWS_CB}{item_id}")])

    if selected_subcategory_id:
        if selected_item_index is not None: # NEW
            back_callback = f"{CAROUSEL_NAV_CB}{selected_subcategory_id}:{selected_item_index}"
        else:
            back_callback = f"{SUBCAT_CB_PREFIX}{selected_subcategory_id}"
        buttons.append(
            [InlineKeyboardButton(text="🔙 Назад (к товарам)", callback_data=back_callback)]
        )
    else:
        buttons.append([InlineKeyboardButton(text="🔙 Назад (к категориям)", callback_data=BACK_TO_CAT)])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_back_to_item_details_keyboard(item_id: int) -> InlineKeyboardMarkup:
    """Собрать клавиатуру возврата к деталям товара."""
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(
            text="🔙 Назад (к деталям товара)",
            callback_data=f"{ITEM_DETAILS_CB}{item_id}"
        )]]
    )