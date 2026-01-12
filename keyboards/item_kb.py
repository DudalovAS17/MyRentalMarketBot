from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_item_confirmation_keyboard(edit_callback: str = "edit_item") -> InlineKeyboardMarkup:
    """ Создаёт инлайн-клавиатуру подтверждения объявления"""
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Опубликовать", callback_data="publish_item")
    kb.button(text="🔄 Изменить",    callback_data="edit_item")
    kb.button(text="❌ Отменить",    callback_data="cancel_item")
    # 1-й ряд: две кнопки, 2-й ряд: одна
    kb.adjust(2, 1)
    return kb.as_markup()


def get_photos_keyboard():
    return ReplyKeyboardMarkup(
        resize_keyboard=True,
        keyboard=[
            [KeyboardButton(text="✅ Готово")],
            [KeyboardButton(text="🔙 Назад")],
        ]
    )