from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_open_rental_keyboard(rental_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Открыть сделку", callback_data=f"rental_details:{rental_id}")],
        ] # "🔍 Посмотреть запрос"
    )