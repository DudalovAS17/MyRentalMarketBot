from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from utils.callbacks import (ITEM_DETAILS_CB, BACK_TO_MENU_CB, MY_RENTALS_CB, RENT_PERIOD_CB, RENT_QUANTITY_CB,
                             RENT_DELIVERY_CB,  CANCEL_RENT_FLOW_CB, CONFIRM_RENT_CB, RENT_SKIP_COMMENT_CB) # RENT_BACK_CB, RENT_CHANGE_CB


PERIOD_OPTIONS: tuple[tuple[str, str, int | None], ...] = (
    ("1d", "1 день", 1),
    ("2_7d", "2–7 дней", None),
    ("8_14d", "8–14 дней", None),
    ("15_plus", "15+ дней", None),
)
PERIOD_LABELS: dict[str, str] = {code: label for code, label, _ in PERIOD_OPTIONS}
PERIOD_DAYS: dict[str, int | None] = {code: days for code, _, days in PERIOD_OPTIONS}


def build_rent_step_keyboard() -> InlineKeyboardMarkup: # *, include_back: bool = True
    """Собрать общую клавиатуру шага заявки с кнопками назад/отмена."""
    rows = [
        #*([[InlineKeyboardButton(text="⬅️ Назад", callback_data=RENT_BACK_CB)]] if include_back else []),
        [InlineKeyboardButton(text="❌ Отменить", callback_data=CANCEL_RENT_FLOW_CB)],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)

# кол-во товара
def build_rent_quantity_keyboard(available_quantity: int) -> InlineKeyboardMarkup:
    """Собрать клавиатуру выбора количества с быстрыми вариантами и ручным вводом."""
    quick_values = [value for value in (1, 2, 3) if value <= max(available_quantity, 1)]
    rows = [
        [InlineKeyboardButton(text=str(value), callback_data=f"{RENT_QUANTITY_CB}{value}") for value in quick_values],
        [InlineKeyboardButton(text="✍️ Ввести другое количество сообщением", callback_data=f"{RENT_QUANTITY_CB}manual")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data=CANCEL_RENT_FLOW_CB)],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)

# диапазон дат
def build_rent_period_keyboard() -> InlineKeyboardMarkup: # item_id: int
    """Собрать клавиатуру выбора фиксированного диапазона аренды."""
    rows = [
        [InlineKeyboardButton(text=label, callback_data=f"{RENT_PERIOD_CB}{code}")]
        for code, label, _ in PERIOD_OPTIONS
    ]
    #rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=RENT_BACK_CB)])
    rows.append([InlineKeyboardButton(text="❌ Отменить", callback_data=CANCEL_RENT_FLOW_CB)]) # "🔙 Назад к товару": f"{ITEM_DETAILS_CB}{item_id}"
    return InlineKeyboardMarkup(inline_keyboard=rows)

# доставка
def build_rent_delivery_keyboard() -> InlineKeyboardMarkup:
    """Собрать клавиатуру выбора доставки или самовывоза."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚚 Нужна доставка", callback_data=f"{RENT_DELIVERY_CB}yes")],
            [InlineKeyboardButton(text="🚫 Самовывоз / без доставки", callback_data=f"{RENT_DELIVERY_CB}no")],
            #[InlineKeyboardButton(text="⬅️ Назад", callback_data=RENT_BACK_CB)],
            [InlineKeyboardButton(text="❌ Отменить", callback_data=CANCEL_RENT_FLOW_CB)],
        ]
    )

# телефон
def build_rent_contact_keyboard(use_profile_callback: str | None) -> InlineKeyboardMarkup:
    """Собрать клавиатуру шага контактов с опциональным использованием профиля."""
    rows: list[list[InlineKeyboardButton]] = []
    if use_profile_callback:
        rows.append([InlineKeyboardButton(text="✅ Использовать из профиля", callback_data=use_profile_callback)])
    #rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=RENT_BACK_CB)])
    rows.append([InlineKeyboardButton(text="❌ Отменить", callback_data=CANCEL_RENT_FLOW_CB)])
    return InlineKeyboardMarkup(inline_keyboard=rows)

# комментарий
def build_rent_comment_keyboard() -> InlineKeyboardMarkup:
    """Собрать клавиатуру шага комментария с возможностью пропуска."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⏭️ Без комментария", callback_data=RENT_SKIP_COMMENT_CB)],
            #[InlineKeyboardButton(text="⬅️ Назад", callback_data=RENT_BACK_CB)],
            [InlineKeyboardButton(text="❌ Отменить", callback_data=CANCEL_RENT_FLOW_CB)],
        ]
    )

# подтверждение заявки
def build_rent_confirmation_keyboard() -> InlineKeyboardMarkup:
    """Собрать клавиатуру подтверждения заявки."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Отправить заявку", callback_data=CONFIRM_RENT_CB)],
            #[InlineKeyboardButton(text="✏️ Изменить", callback_data=RENT_CHANGE_CB)],
            #[InlineKeyboardButton(text="⬅️ Назад", callback_data=RENT_BACK_CB)],
            [InlineKeyboardButton(text="❌ Отменить", callback_data=CANCEL_RENT_FLOW_CB)],
        ]
    )

# успешно
def build_rent_success_keyboard() -> InlineKeyboardMarkup:
    """Собрать клавиатуру после успешной отправки заявки."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📋 Мои аренды", callback_data=MY_RENTALS_CB)],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data=BACK_TO_MENU_CB)],
        ]
    )

# отмена
def build_rent_cancel_keyboard(item_id: int | None) -> InlineKeyboardMarkup:
    """Собрать клавиатуру после отмены заявки."""
    rows: list[list[InlineKeyboardButton]] = []

    if item_id is not None:
        rows.append([InlineKeyboardButton(text="🔙 Назад к товару", callback_data=f"{ITEM_DETAILS_CB}{item_id}")])

    rows.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data=BACK_TO_MENU_CB)])

    return InlineKeyboardMarkup(inline_keyboard=rows)
