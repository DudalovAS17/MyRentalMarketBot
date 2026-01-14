from aiogram.types import Message, CallbackQuery
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



async def deny(
    event: Message | CallbackQuery,
    message_text: str,
    *,
    alert_text: str | None = None,
    show_alert: bool = True,
):
    """
    Унифицированный ответ пользователю.

    - CallbackQuery:
        - убирает "часики"
        - показывает alert (если задан)
        - отправляет сообщение в чат
    - Message:
        - просто отвечает сообщением
    """
    if isinstance(event, CallbackQuery):
        if alert_text:
            await event.answer(alert_text, show_alert=show_alert)
        return await event.message.answer(message_text)
    """
    alert: “Нет доступа” → мгновенно понятно, почему кнопка не работает
    сообщение в чат: “⛔ Доступ запрещён. Только администраторам.” → остаётся, можно перечитать
    👉 Это правильный UX.
    """

    return await event.answer(message_text)

# В чём разница между show_alert=True и show_alert=False
"""
🔹 show_alert=False (по умолчанию)
    Показывает маленький всплывающий toast внизу экрана
    Автоматически исчезает
    Не блокирует интерфейс

Хорошо для:
    подтверждений (“Готово”, “Сохранено”)
    мягких уведомлений
Пример: await callback.answer("Сохранено", show_alert=False)


🔹 show_alert=True
    Показывает модальное окно (alert) в центре экрана
    Требует нажатия “OK”
    Блокирует UI, пока не закрыто

Хорошо для:
    ошибок
    запретов доступа
    критичных сообщений

Пример:  await callback.answer("Нет доступа", show_alert=True)

📌 В админке и проверках прав — почти всегда True.
"""