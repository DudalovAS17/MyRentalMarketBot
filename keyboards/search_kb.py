from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def build_search_keyboard(items, page: int, has_next: bool) -> InlineKeyboardMarkup:
    keyboard: list[list[InlineKeyboardButton]] = []

    for item in items:
        keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"🔎 Открыть #{item.id}",
                    callback_data=f"show_item_details:{item.id}",
                )
            ]
        )

    has_prev = page > 1
    nav_row: list[InlineKeyboardButton] = []
    if has_prev:
        nav_row.append(InlineKeyboardButton(text="⬅️ Пред", callback_data=f"search:page:{page - 1}"))
    if has_next:
        nav_row.append(InlineKeyboardButton(text="➡️ След", callback_data=f"search:page:{page + 1}"))
    if nav_row:
        keyboard.append(nav_row)

    keyboard.append([InlineKeyboardButton(text="✏️ Новый запрос", callback_data="search:new_query")])
    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="search:back")]) # "back_to_main_menu"

    return InlineKeyboardMarkup(inline_keyboard=keyboard)