from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

BACK_TO_MENU_CB = ""

def cancel_keyboard() -> InlineKeyboardMarkup:
    """Единая inline-клавиатура для FSM: только ❌ Отмена → главное меню."""
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="❌ Отмена", callback_data=BACK_TO_MENU_CB)]]
    )

def get_photos_keyboard():
    return ReplyKeyboardMarkup(
        resize_keyboard=True,
        keyboard=[[KeyboardButton(text="✅ Готово")]]
            #[KeyboardButton(text="🔙 Назад")],
    )