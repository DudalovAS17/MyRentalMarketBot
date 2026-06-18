from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton


def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура главного меню клиента (с учетом информации о нем)"""
    keyboard = [
        [KeyboardButton(text="🔍 Арендовать"), KeyboardButton(text="🔎 Поиск")],
        [KeyboardButton(text="📋 Мои сделки"), KeyboardButton(text="👤 Профиль")],
        [KeyboardButton(text="📞 Поддержка"), KeyboardButton(text="❓ Помощь")],
    ]

    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True, input_field_placeholder="Выберите действие")


def get_back_inline_keyboard(step_callback: str = None) -> InlineKeyboardMarkup:
    """Клавиатуру возврата

    - Назад (на предыдущий шаг)
    - Отмена (в меню) """

    if step_callback:
        buttons = [[InlineKeyboardButton(text="⬅️ Назад", callback_data=step_callback),
                    InlineKeyboardButton(text="❌ Отмена", callback_data="back_to_main_menu")]] # "back_to_menu"
    else:
        buttons = [[InlineKeyboardButton(text="❌ Отмена", callback_data="back_to_main_menu")]] # "back_to_menu"

    return InlineKeyboardMarkup(inline_keyboard=buttons)




