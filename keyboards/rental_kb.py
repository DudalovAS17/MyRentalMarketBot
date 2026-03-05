from datetime import date, timedelta
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

CANCEL_RENT_FLOW_CB = "cancel_rent_flow"
START_DATE_CB = "start_date:"
CONFIRM_RENT_CB = "confirm_rent"

def get_open_rental_keyboard(rental_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Открыть сделку", callback_data=f"rental_details:{rental_id}")],
        ] # "🔍 Посмотреть запрос"
    )

def build_rent_end_date_keyboard(start_date: date, min_days: int, max_days: int, options: int = 6) -> InlineKeyboardMarkup:
    """
    Клавиатура выбора даты окончания аренды.
    Показываем 'options' вариантов начиная с min_days, но не выходя за max_days.
    """

    min_days = max(min_days, 1)
    max_days = max(max_days, min_days)

    # Покажем до 6 вариантов: min_days ... min_days + options, но не больше max_days
    option_days = [d for d in range(min_days, min_days + options) if d <= max_days] or [min_days]

    rows: list[list[InlineKeyboardButton]] = [
        [InlineKeyboardButton(text="📅 Выберите дату окончания аренды:", callback_data="ignore")]
    ]

    for days in option_days:
        end_date = start_date + timedelta(days=days)
        end_str = end_date.strftime("%d.%m.%Y")
        rows.append(
            [InlineKeyboardButton(text=f"{end_str}  ({days} дн.)", callback_data=f"end_date:{end_str}:{days}")]
        )

    rows.append([InlineKeyboardButton(text="❌ Отмена", callback_data=CANCEL_RENT_FLOW_CB)])
    #rows.append([InlineKeyboardButton(text="🔙 Назад к выбору даты начала", callback_data=f"rent_item:{item_id}")])

    return InlineKeyboardMarkup(inline_keyboard=rows)

def build_rent_confirmation_keyboard(start_date: str) -> InlineKeyboardMarkup:
    """Клавиатура финального шага подтверждения аренды."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Отправить запрос владельцу", callback_data=CONFIRM_RENT_CB)],
            [InlineKeyboardButton(text="🔙 Изменить дату окончания", callback_data=f"{START_DATE_CB}{start_date}")],
            [InlineKeyboardButton(text="❌ Отменить аренду", callback_data=CANCEL_RENT_FLOW_CB)], # или f"{ITEM_DETAILS}{item_id}"???
        ]
    )