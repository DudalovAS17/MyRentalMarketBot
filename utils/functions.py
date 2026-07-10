from typing import Optional
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, ReplyMarkupUnion
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext

TgEvent = Message | CallbackQuery

async def send_or_edit(
        event: TgEvent,
        text: str,
        markup: InlineKeyboardMarkup | None = None,
        parse_mode: str | None = "HTML",
) -> Message:
    """Унифицированная отправка/редактирование сообщения:
        - CallbackQuery → Редактирует сообщение (при ошибке → send_message)
            если Telegram не может превратить фото-сообщение в текст, удаляет старое и отправляет замену
        - Message → отправляет новое
    """
    if isinstance(event, CallbackQuery):
        try:
            return await event.message.edit_text(text, reply_markup=markup, parse_mode=parse_mode)
        except TelegramBadRequest:
            if event.message.photo:
                try:
                    await event.message.delete()
                except TelegramBadRequest:
                    pass
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