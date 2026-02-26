from typing import Sequence
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from schemas.item import ItemOut

BACK_TO_MENU_CB = "back_to_main_menu" # "back_to_menu"
ADD_ITEM_CB = "add_item"
SHOW_ITEM_CB = "show_item:"
MY_ITEMS_PREFIX = "my_items"

EDIT_ITEM_CB = "edit_item"
EDIT_FIELD_CB = "edit_field:"
SHOW_ITEM_CB = "show_item:"

def build_my_items_keyboard(items: Sequence[ItemOut]) -> InlineKeyboardMarkup:
    """
    Клавиатура экрана «Мои объявления».
    Работает в двух режимах:
    - items пустой: только «Добавить» + «Назад в меню»
    - items есть: «Добавить» + список объявлений + «Назад в меню»
    """
    rows: list[list[InlineKeyboardButton]] = [
        [InlineKeyboardButton(text="➕ Добавить объявление", callback_data=ADD_ITEM_CB)]
    ]

    for item in items: # Добавляем кнопки для каждого объявления
        status = "✅ Активно" if item.is_available else "❌ Не активно"
        rows.append(
            [InlineKeyboardButton(text=f"{item.title} ({status})", callback_data=f"{SHOW_ITEM_CB}{item.id}")]
        ) # Тут по имени отсев, но потом надо по id ?

    rows.append([InlineKeyboardButton(text="🔙 Назад в меню", callback_data=BACK_TO_MENU_CB)])

    return InlineKeyboardMarkup(inline_keyboard=rows)

def build_my_item_details_keyboard(item: ItemOut) -> InlineKeyboardMarkup:
    """Клавиатура экрана деталей объявления (внутри «Мои объявления»)"""

    rows: list[list[InlineKeyboardButton]] = []

    # Переключатель статуса
    if item.is_available:
        rows.append(
            [InlineKeyboardButton(text="❌ Сделать недоступным", callback_data=f"toggle_available:{item.id}")]
        )
    else:
        rows.append(
            [InlineKeyboardButton(text="✅ Сделать доступным", callback_data=f"toggle_available:{item.id}")]
        )

    rows.append(
        [
            InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"{EDIT_ITEM_CB}{item.id}"),
            InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"delete_item:{item.id}"),
        ]
    )

    rows.append([InlineKeyboardButton(text="🔙 Назад (к моим объявлениям)", callback_data=MY_ITEMS_PREFIX)])

    return InlineKeyboardMarkup(inline_keyboard=rows)

""" Убираем эту логику
def get_back_inline_keyboard(step_callback: str = None) -> InlineKeyboardMarkup:
    "" Создает inline-клавиатуру с кнопками возврата:
    - Назад (на предыдущий шаг) - step_callback (callback (str): данные, которые вернутся в callback при нажатии)
    - Отмена (в меню)""

    if step_callback:
        buttons = [
            [
                InlineKeyboardButton(text="⬅️ Назад", callback_data=step_callback),
                InlineKeyboardButton(text="❌ Отмена", callback_data=BACK_TO_MENU_CB)
            ]
        ]
    else:
        buttons = [
            [InlineKeyboardButton(text="❌ Отмена", callback_data=BACK_TO_MENU_CB)]
        ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)
"""

def cancel_keyboard() -> InlineKeyboardMarkup:
    """Единая inline-клавиатура для FSM: только ❌ Отмена → главное меню."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data=BACK_TO_MENU_CB)]
        ]
    )

# def get_item_confirmation_keyboard(edit_callback: str = "edit_item") -> InlineKeyboardMarkup:
#     """ Создаёт inline-клавиатуру подтверждения объявления"""
#     kb.button(text="✅ Опубликовать", callback_data="publish_item")
#     kb.button(text="🔄 Изменить",    callback_data=EDIT_ITEM_CB)
#     kb.button(text="❌ Отменить",    callback_data="cancel_item")

def get_photos_keyboard():
    return ReplyKeyboardMarkup(
        resize_keyboard=True,
        keyboard=[
            [KeyboardButton(text="✅ Готово")],
            #[KeyboardButton(text="🔙 Назад")],
        ]
    )

def build_edit_item_keyboard(item_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📝 Название", callback_data=f"{EDIT_FIELD_CB}title")],
            [InlineKeyboardButton(text="📋 Описание", callback_data=f"{EDIT_FIELD_CB}description")],
            [InlineKeyboardButton(text="💰 Цена", callback_data=f"{EDIT_FIELD_CB}price")],
            [InlineKeyboardButton(text="🔐 Залог", callback_data=f"{EDIT_FIELD_CB}deposit")],
            [InlineKeyboardButton(text="📍 Местоположение", callback_data=f"{EDIT_FIELD_CB}location")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data=f"{SHOW_ITEM_CB}{item_id}")],
        ]
    )


