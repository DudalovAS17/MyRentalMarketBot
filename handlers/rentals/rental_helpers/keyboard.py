from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from utils.callbacks import ITEM_DETAILS, BACK_TO_MENU_CB, MY_RENTALS_CB, RENT_PERIOD_CB

PERIOD_OPTIONS: tuple[tuple[str, str, int | None], ...] = (
    ("1d", "1 день", 1),
    ("2_7d", "2–7 дней", None),
    ("8_14d", "8–14 дней", None),
    ("15_plus", "15+ дней", None),
)
PERIOD_LABELS: dict[str, str] = {code: label for code, label, _ in PERIOD_OPTIONS}
PERIOD_DAYS: dict[str, int | None] = {code: days for code, _, days in PERIOD_OPTIONS}

def build_rent_period_keyboard(item_id: int) -> InlineKeyboardMarkup:
    """Собрать клавиатуру выбора фиксированного диапазона аренды."""
    rows = [
        [InlineKeyboardButton(text=label, callback_data=f"{RENT_PERIOD_CB}{code}")]
        for code, label, _ in PERIOD_OPTIONS
    ]
    rows.extend(
        [
            #[InlineKeyboardButton(text="✍️ Ввести кол-во дней", callback_data=CUSTOM_RENT_DATES_CB)],
            [InlineKeyboardButton(text="🔙 Назад к товару", callback_data=f"{ITEM_DETAILS}{item_id}")],
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)

def build_rent_cancel_keyboard(item_id: int | None) -> InlineKeyboardMarkup:
    """Собрать клавиатуру экрана отмены rent-flow"""
    rows: list[list[InlineKeyboardButton]] = []

    if item_id is not None:
        rows.append([InlineKeyboardButton(text="🔙 Назад к товару", callback_data=f"{ITEM_DETAILS}{item_id}")])

    rows.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data=BACK_TO_MENU_CB)])

    return InlineKeyboardMarkup(inline_keyboard=rows)

def build_rent_success_keyboard() -> InlineKeyboardMarkup:
    """Собрать клавиатуру после успешной отправки заявки."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📋 Мои аренды", callback_data=MY_RENTALS_CB)],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data=BACK_TO_MENU_CB)],
        ]
    )