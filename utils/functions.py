from typing import Optional
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, ReplyMarkupUnion
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext

TgEvent = Message | CallbackQuery

"""
send_or_edit - Унифицированная отправка/редактирование сообщения:
    - CallbackQuery → Редактирует сообщение (при ошибке → send_message)
    - Message → отправляет новое
    
send_reply - Унифицированная отправка сообщения

deny - Унифицированный ответ пользователю: показывает отказ и оставляет понятное сообщение в чате.
    alert: “Нет доступа” → мгновенно понятно, почему кнопка не работает
    сообщение в чат: “⛔ Доступ запрещён. Только администраторам.” → остаётся, можно перечитать
    👉 Это правильный UX.

---------------------------------

abort_rent_flow():
Это функция для аварийного завершения сценария аренды. 
Например: пользователь начал аренду, но товар уже недоступен, данные в FSM устарели, аренда не может быть продолжена и т.д.
“Показать ошибку и остановить сценарий аренды”

render_rent_ui - Это функция для обычного отображения UI сценария аренды.
Почему render_rent_ui не чистит FSM: Это правильно, потому что render_rent_ui используется в нормальном рабочем сценарии аренды. 
После рендера пользователю нужно продолжить flow: нажать кнопку, выбрать дату, подтвердить аренду и т.д.

Замечание: abort_rent_flow и render_rent_ui содержат Telegram-логику (bot.edit_message_text). 
Это допустимо для utils (они — часть UI-слоя), но не должны появляться в services.

_send_or_update_rent_ui():
“У меня есть текст и, возможно, клавиатура. Попробуй показать это в существующем rent-UI сообщении. 
Если не получилось — создай новое. Верни id актуального сообщения”.
"""

""" В чём разница между show_alert=True и show_alert=False

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

async def send_or_edit(
        event: TgEvent,
        text: str,
        markup: InlineKeyboardMarkup | None = None,
        parse_mode: str | None = "HTML",
) -> Message:
    """Унифицированная отправка/редактирование сообщения:
        - CallbackQuery → Редактирует сообщение (при ошибке → send_message)
        - Message → отправляет новое
    """
    if isinstance(event, CallbackQuery):
        try:
            return await event.message.edit_text(text, reply_markup=markup, parse_mode=parse_mode)
        except TelegramBadRequest:
            return await event.message.answer(text, reply_markup=markup, parse_mode=parse_mode)
    else:
        return await event.answer(text, reply_markup=markup, parse_mode=parse_mode)

async def send_reply(
        event: TgEvent,
        text: str,
        markup: ReplyMarkupUnion | None = None, # ReplyMarkupUnion = InlineKeyboardMarkup + ReplyKeyboardMarkup
        parse_mode: str | None = "HTML",
) -> Message:
    """Унифицированная отправка сообщения с inline- или reply-клавиатурой."""
    if isinstance(event, CallbackQuery):
        return await event.message.answer(text, reply_markup=markup, parse_mode=parse_mode)

    return await event.answer(text, reply_markup=markup, parse_mode=parse_mode)

async def deny(
    event: TgEvent,
    message_text: str,
    *,
    alert_text: str | None = None,
    show_alert: bool = True,
) -> Message:
    """Унифицированный ответ пользователю: показывает отказ и оставляет понятное сообщение в чате."""
    if isinstance(event, CallbackQuery):
        if alert_text:
            await event.answer(alert_text, show_alert=show_alert) # убирает "часики" и показывает alert
        return await event.message.answer(message_text)

    return await event.answer(message_text)

# ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
# err_text = "❌ Ошибка. Попробуйте начать аренду заново."
async def abort_rent_flow(
        event: TgEvent,
        state: FSMContext,
        err_text: str,
        rent_ui_message_id: Optional[int] = None,
) -> None:
    """Аварийное завершение сценария аренды: показать ошибку сценария аренды и очистить FSM-данные."""
    await _send_or_update_rent_ui(event, state, err_text, rent_ui_message_id=rent_ui_message_id)

    await state.clear()


async def render_rent_ui(
    event: TgEvent,
    state: FSMContext,
    err_text: str,
    keyboard: Optional[InlineKeyboardMarkup] = None,
    rent_ui_message_id: Optional[int] = None,
) -> None:
    """Обычный рендер rent-UI: обновляет или создаёт UI-сообщение аренды и возвращает его id. Не чистит state.
    Сохраняет новый message_id при необходимости.
    """
    await _send_or_update_rent_ui(event, state, err_text,
        keyboard=keyboard, rent_ui_message_id=rent_ui_message_id, save_message_id=True
    )

# helper для обеих функций
async def _send_or_update_rent_ui(
    event: TgEvent,
    state: FSMContext,
    err_text: str,
    *,
    keyboard: InlineKeyboardMarkup | None = None,
    rent_ui_message_id: int | None = None,
    save_message_id: bool = False,
) -> int:
    """Обновляет UI-сообщение аренды или отправляет новое."""
    message = event.message if isinstance(event, CallbackQuery) else event

    # если id не передали — пробуем взять из state
    if rent_ui_message_id is None:
        data = await state.get_data()
        rent_ui_message_id = data.get("rent_ui_message_id")

    # Если id есть — отредактировать старое сообщение
    if rent_ui_message_id:
        try:
            await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=rent_ui_message_id,
                text=err_text,
                reply_markup=keyboard,
                parse_mode="HTML",
            )
            return int(rent_ui_message_id)
        except TelegramBadRequest:
            pass

    # Если отредактировать нельзя — отправляет новое сообщение
    # (например, если старое сообщение уже нельзя редактировать или Telegram вернул TelegramBadRequest)
    sent = await message.answer(err_text, reply_markup=keyboard, parse_mode="HTML")
    if save_message_id: # При необходимости сохраняет новый message_id
        await state.update_data(rent_ui_message_id=sent.message_id)
    return sent.message_id # Возвращает актуальный message_id