from aiogram.types import Message, CallbackQuery
from aiogram.exceptions import TelegramBadRequest


def format_price(price: int | float) -> str:
    return f"{price:,.2f}".replace(",", " ").replace(".00", "")


# Вспомогательная функция для send/edit
async def send_or_edit(event, text, markup):
    """Унифицированная отправка или редактирование сообщения.
        - CallbackQuery → edit_message_text, при ошибке → send_message
        - Message → answer()
    """
    if isinstance(event, CallbackQuery):
        try:
            return await event.message.edit_text(
                text, reply_markup=markup, parse_mode="HTML"
            )
        except TelegramBadRequest:
            return await event.message.answer(text, reply_markup=markup, parse_mode="HTML")
    else:
        return await event.answer(text, reply_markup=markup, parse_mode="HTML")