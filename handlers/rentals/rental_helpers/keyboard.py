from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timezone, timedelta

from utils.callbacks import (ITEM_DETAILS, START_DATE_CB, BACK_TO_MENU_CB, MY_RENTALS_CB, IGNORE_CB, START_DATE_DAYS_AHEAD)


def build_start_date_keyboard(item_id: int, days_ahead: int = START_DATE_DAYS_AHEAD) -> InlineKeyboardMarkup:
    """Собирает клавиатуру выбора даты начала аренды."""

    # Формируем кнопки выбора даты начала
    today = datetime.now(timezone.utc)
    rows = [[InlineKeyboardButton(text="📅 Выберите дату начала аренды:", callback_data=IGNORE_CB)]] # dummy_start

    for i in range(1, days_ahead + 1):
        date = today + timedelta(days=i)
        ds = date.strftime("%d.%m.%Y") # для кнопок
        rows.append([InlineKeyboardButton(text=ds, callback_data=f"{START_DATE_CB}{ds}")])

    rows.append([
        InlineKeyboardButton(text="🔙 Назад к объявлению", callback_data=f"{ITEM_DETAILS}{item_id}")
    ]) # убираем?

    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_rent_cancel_keyboard(item_id: int | None) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []

    if item_id:
        rows.append([InlineKeyboardButton(text="🔙 К объявлению", callback_data=f"{ITEM_DETAILS}{item_id}")])

    rows.append([
        InlineKeyboardButton(text="🏠 Главное меню", callback_data=BACK_TO_MENU_CB)])

    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_rent_success_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📋 Мои сделки", callback_data=MY_RENTALS_CB)],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data=BACK_TO_MENU_CB)],
        ]
    )
