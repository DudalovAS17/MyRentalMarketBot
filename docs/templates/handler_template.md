**Template: Handler**

Правила:
- Только UX/FSM/Router
- Никаких ORM/SQLAlchemy
- Минимум логики



```
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from services.example_service import ExampleService
from utils.callbacks import parse_int_id_from_callback
from utils.functions import send_or_edit
from utils.formatters import format_example_message  # условно

logger = logging.getLogger(__name__)
example_router = Router()


@example_router.message(F.text == "/example")
async def handle_example_message(
    message: Message,
    state: FSMContext,
    example_service: ExampleService,
) -> None:
    """UX/FSM: обработка команды /example. Минимальная обработка входа → вызов сервиса → ответ."""
    await message.answer("Получаю данные…")

    telegram_user_id = message.from_user.id

    try:
        payload = await example_service.get_example_payload(telegram_user_id=telegram_user_id)
    except Exception as exc:
        logger.error("handle_example_message(): %s", exc, exc_info=True)
        await message.answer("⚠️ Не удалось получить данные.")
        return

    response_text = format_example_message(payload)
    await message.answer(response_text)


@example_router.callback_query(F.data.startswith("example:"))
async def handle_example_callback(
    callback: CallbackQuery,
    example_service: ExampleService,
) -> None:
    """UX: обработка callback-кнопки. Парсим вход → сервис → update UI."""
    await callback.answer()

    example_id = await parse_int_id_from_callback(callback)
    if example_id is None:
        return

    try:
        payload = await example_service.get_example_details(example_id=example_id)
    except Exception as exc:
        logger.error("handle_example_callback(): %s", exc, exc_info=True)
        await callback.answer("Ошибка при загрузке", show_alert=True)
        return

    await send_or_edit(callback, format_example_message(payload))