from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup
from aiogram.exceptions import TelegramBadRequest

def format_price(price: int | float) -> str:
    return f"{price:,.2f}".replace(",", " ").replace(".00", "")

# Вспомогательная функция для send/edit - для INLINE-клав
async def send_or_edit(event, text, markup=None, parse_mode="HTML"):
    """Унифицированная отправка или редактирование сообщения.
        - CallbackQuery → edit_message_text (при ошибке → send_message)
        - Message → answer()
    """
    if isinstance(event, CallbackQuery):
        try:
            return await event.message.edit_text(
                text, reply_markup=markup, parse_mode=parse_mode
            )
        except TelegramBadRequest:
            return await event.message.answer(text, reply_markup=markup, parse_mode=parse_mode)
    else:
        return await event.answer(text, reply_markup=markup, parse_mode=parse_mode)

# Вспомогательная функция для send - для REPLY-клав
async def send_reply(event, text: str, reply_markup=None, parse_mode: str = "HTML"):
    """Унифицированная отправка сообщения для ReplyKeyboardMarkup (и вообще для обычного send)
        - CallbackQuery → message.answer()
        - Message → answer()
    """
    if isinstance(event, CallbackQuery):
        return await event.message.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)

    return await event.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)
