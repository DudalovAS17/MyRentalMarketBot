from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import Sequence
from schemas.category import CategoryOut
from schemas.item import ItemOut

RENT_ITEM_CB = "rent_item:"
SHOW_ALL_PHOTOS_CB = "show_all_photos:"
MESSAGE_OWNER_CB = "message_owner:"
REVIEWS_CB = "reviews:"
SUBCAT_CB_PREFIX = "subcat:"
BACK_TO_CAT = "back_to_categories"


"""
build_category_keyboard() универсальный: 
- один и тот же билдер подходит для:
    - категорий (нужны “🏙️ город / ⚙️ фильтры / 🔙 меню”)
    - подкатегорий (нужны “📋 все в категории / 🔙 назад”)
    - админских списков (нужны “➕ создать / ❌ отмена”)
- Билдер не “знает” бизнес-сценарий, он просто строит кнопки.
- Хендлер/Ui-builder решает какие дополнительные кнопки нужны.
То есть extra_buttons — это как “слот” в UI-компоненте. 👌
"""

def build_category_keyboard(
    categories: Sequence[CategoryOut], # Ты передаёшь list[CategoryOut] → а list является Sequence, значит всё ок.
    prefix: str,
    *,
    #buttons_per_row: int = 2,
    extra_buttons: list[list[InlineKeyboardButton]] | None = None
) -> InlineKeyboardMarkup:
    """
    Универсальный генератор клавиатур для категорий / подкатегорий.

    Args:
        categories: Pydantic-модель - CategoryOut (cat.id, cat.name, cat.emoji)
        prefix: префикс callback_data (например 'create_cat:' или 'browse_cat:')
        #buttons_per_row: количество кнопок в строке
        extra_buttons: дополнительные кнопки (например 'Назад' или 'Отмена')

    Returns:
        InlineKeyboardMarkup
    """

    # строим клавиатуру (2 кнопки в ряд)
    rows: list[list[InlineKeyboardButton]] = [] # keyboard_rows
    row: list[InlineKeyboardButton] = []

    for i, cat in enumerate(categories, start=1):
        btn_text = f"{(cat.emoji or '').strip()} {cat.name}".strip() # "🏕️ Туризм и спорт"
        btn_cb = f"{prefix}{cat.id}" # CAT_CB_PREFIX
        row.append(InlineKeyboardButton(text=btn_text, callback_data=btn_cb))

        if i % 2 == 0: # i % buttons_per_row
            rows.append(row)
            row = []

    if row:
        rows.append(row)

    if extra_buttons:
        rows.extend(extra_buttons)

    return InlineKeyboardMarkup(inline_keyboard=rows)




def build_items_keyboard(
    items: Sequence[ItemOut],
    *,
    parent_category_id: int,
    item_details_cb_prefix: str,
    cat_cb_prefix: str,
    back_text: str = "🔙 Назад (к подкатегориям)",
) -> InlineKeyboardMarkup:
    """
    Строит клавиатуру списка объявлений внутри подкатегории.

    items: iterable объектов с полями title, price, id
    parent_category_id: id родительской категории (для кнопки назад)
    item_details_cb_prefix: префикс callback для деталей объявления (например "show_item_details:")
    cat_cb_prefix: префикс callback для категории (например "cat:")
    """

    keyboard_rows: list[list[InlineKeyboardButton]] = []

    for item in items:
        btn_text = f"📦 {item.title} — {item.price} ₽/день"
        btn_cb = f"{item_details_cb_prefix}{item.id}" # show_item_details:
        keyboard_rows.append([InlineKeyboardButton(text=btn_text, callback_data=btn_cb)])

    # Кнопка назад
    keyboard_rows.append(
        [InlineKeyboardButton(text=back_text, callback_data=f"{cat_cb_prefix}{parent_category_id}")]
    )

    return InlineKeyboardMarkup(inline_keyboard=keyboard_rows)


def build_item_details_kb(
    item_id: int,
    *,
    is_busy: bool,
    selected_subcategory_id: int | None,
    end_date: str | None,
) -> InlineKeyboardMarkup:
    buttons: list[list[InlineKeyboardButton]] = []

    if is_busy:
        button_text = f"⛔ Сейчас занято (до {end_date})" if end_date else "⛔ Сейчас занято"
        buttons.append([InlineKeyboardButton(text=button_text, callback_data="noop")])
    else:
        buttons.append([InlineKeyboardButton(text="✅ Арендовать", callback_data=f"{RENT_ITEM_CB}{item_id}")])

    buttons.append([InlineKeyboardButton(text="📸 Показать все фото", callback_data=f"{SHOW_ALL_PHOTOS_CB}{item_id}")])
    buttons.append([InlineKeyboardButton(text="💬 Написать владельцу", callback_data=f"{MESSAGE_OWNER_CB}{item_id}")])
    buttons.append([InlineKeyboardButton(text="⭐ Отзывы", callback_data=f"{REVIEWS_CB}{item_id}")])

    if selected_subcategory_id:
        buttons.append(
            [InlineKeyboardButton(text="🔙 Назад (к объявлениям)", callback_data=f"{SUBCAT_CB_PREFIX}{selected_subcategory_id}")]
        )
    else:
        buttons.append([InlineKeyboardButton(text="🔙 Назад (к категориям)", callback_data=BACK_TO_CAT)])

    return InlineKeyboardMarkup(inline_keyboard=buttons)
