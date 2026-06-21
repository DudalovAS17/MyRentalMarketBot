from typing import Optional
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup
from aiogram.exceptions import TelegramBadRequest
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from aiogram.fsm.context import FSMContext

# Вспомогательная функция для send/edit
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
            #logger.warning("Не удалось отредактировать сообщение подкатегорий: %s", e) # списка объявлений # категорий
            return await event.message.answer(text, reply_markup=markup, parse_mode=parse_mode)
    else:
        return await event.answer(text, reply_markup=markup, parse_mode=parse_mode)

# Вспомогательная функция для send
async def send_reply(event, text: str, markup=None, parse_mode: str = "HTML"):
    """Унифицированная отправка сообщения
        - CallbackQuery → message.answer()
        - Message → answer()
    """
    if isinstance(event, CallbackQuery):
        return await event.message.answer(text, reply_markup=markup, parse_mode=parse_mode)

    return await event.answer(text, reply_markup=markup, parse_mode=parse_mode)


async def deny(
    event: Message | CallbackQuery,
    message_text: str,
    *,
    alert_text: str | None = None,
    show_alert: bool = True,
):
    """Унифицированный ответ пользователю"""
    if isinstance(event, CallbackQuery):
        if alert_text:
            await event.answer(alert_text, show_alert=show_alert) # убирает "часики" и показывает alert (если задан)
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


# ---------------------------------------------------------------------------------------------
"""
Замечание: abort_rent_flow и render_rent_ui содержат Telegram-логику (bot.edit_message_text). 
Это допустимо для utils (они — часть UI-слоя), но не должны появляться в services.
"""

async def abort_rent_flow(
        callback: Message | CallbackQuery,
        state: FSMContext,
        err_text: str,
        rent_ui_message_id: Optional[int] = None,
) -> None:
    """Показывает ошибку в rent-UI (если есть) и очищает FSM rent-flow."""

    message = callback.message if isinstance(callback, CallbackQuery) else callback
    chat_id = message.chat.id

    # если id не передали — пробуем взять из state
    if rent_ui_message_id is None:
        data = await state.get_data()
        rent_ui_message_id = data.get("rent_ui_message_id")

    if rent_ui_message_id:
        try:
            await message.bot.edit_message_text(
                chat_id=chat_id,
                message_id=rent_ui_message_id,
                text=err_text,
                parse_mode="HTML",
            )
        except TelegramBadRequest:
            await message.answer(err_text, parse_mode="HTML")
    else:
        await message.answer(err_text, parse_mode="HTML")
        # await send_or_edit(callback, err_text)

    await state.clear() # Очищаем некорректные данные


async def render_rent_ui(
    callback: CallbackQuery,
    state: FSMContext,
    text: str,
    keyboard: Optional[InlineKeyboardMarkup] = None,
    rent_ui_message_id: Optional[int] = None,
) -> int:
    """Обновляет rent-UI сообщение (если есть) или создаёт новое. ✅ НЕ чистит state.
    Возвращает актуальный message_id"""

    chat_id = callback.message.chat.id

    # если id не передали — пробуем взять из state
    if rent_ui_message_id is None:
        data = await state.get_data()
        rent_ui_message_id = data.get("rent_ui_message_id")

    if rent_ui_message_id:
        try:
            await callback.bot.edit_message_text(
                chat_id=chat_id,
                message_id=rent_ui_message_id,
                text=text, # "❌ Ошибка. Попробуйте начать аренду заново."
                reply_markup=keyboard,
                parse_mode="HTML",
            )
            return rent_ui_message_id
        except TelegramBadRequest:
            pass

    sent = await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    await state.update_data(rent_ui_message_id=sent.message_id)
    return sent.message_id
# ---------------------------------------------------------------------------------------------

# def format_price(price: int | float) -> str:
#     return f"{price:,.2f}".replace(",", " ").replace(".00", "")

# разбери
def format_price(price: int | float | Decimal | str | None) -> str:
    """
    Форматирует цену:
    - разделители тысяч пробелом
    - 2 знака после запятой (если они не нули — показываем, иначе убираем)
    Примеры: 12000 -> "12 000", Decimal("12.50") -> "12.5", Decimal("12.00") -> "12"
    """
    if price is None:
        return "—"

    try:
        d = price if isinstance(price, Decimal) else Decimal(str(price))
    except (InvalidOperation, ValueError, TypeError):
        return "—"

    # Денежное округление до копеек
    d = d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    # Строка без экспоненты
    s = format(d, "f")

    # Убираем хвостовые нули и точку, если стало целым
    if "." in s:
        s = s.rstrip("0").rstrip(".")

    # Добавляем разделители тысяч
    if "." in s:
        int_part, frac_part = s.split(".", 1)
        int_part = f"{int(int_part):,}".replace(",", " ")
        return f"{int_part}.{frac_part}"
    else:
        return f"{int(s):,}".replace(",", " ")

def format_days(n: int) -> str:
    if n % 10 == 1 and n % 100 != 11: # n % 10 == 1 (последняя цифра = 1) пропускает 1, (11), 21, 31, 101
        return "день"
    if 2 <= n % 10 <= 4 and not (12 <= n % 100 <= 14):
        return "дня"
    return "дней"

def format_step(title: str, step: int, total: int) -> str:
    """Возвращает форматированный заголовок с прогрессом"""
    progress = f"<b>Шаг {step} из {total}</b>\n\n"
    return f"{progress}{title}"