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
from utils.errors import ServiceError, NotFoundError
from utils.functions import send_or_edit
from utils.formatters import format_example_message

logger = logging.getLogger(__name__)
example_router = Router()


@example_router.message(F.text == "/example")
async def handle_example_message(
    message: Message,
    state: FSMContext,
    example_service: ExampleService,
) -> None:
    """UX/FSM: обработка команды /example. 
    Минимальная обработка входа → вызов сервиса → ответ."""
    
    await message.answer("Получаю данные…")

    telegram_user_id = message.from_user.id

    # В хендлере обрабатываем только бизнес-ошибки сервисов.
    # Технические исключения не перехватываем здесь (они должны уходить в global error handler).
    try:
        payload = await example_service.get_example_payload
            (
                telegram_user_id=telegram_user_id,
                strict=False
            )
    except ServiceError as exc:
        # Бизнес-ошибка -> короткий UX-ответ без stacktrace
        logger.error("handle_example_message(): %s", exc, exc_info=True)
        await message.answer("⚠️ Не удалось получить данные.")
        return

    # payload может быть None (strict=False). Форматтер должен уметь это обработать.
    response_text = format_example_message(payload)
    await message.answer(response_text)


@example_router.callback_query(F.data.startswith("example:"))
async def handle_example_callback(
    callback: CallbackQuery,
    example_service: ExampleService,
) -> None:
    """UX: обработка callback-кнопки. 
    Парсим вход → сервис → обновление UI."""
    await callback.answer()

    example_id = await parse_int_id_from_callback(callback)
    if example_id is None:
        # parse_int_id_from_callback сам должен показать корректный UX-ответ (alert)
        return

    try:
        payload = await example_service.get_example_details
        (
            example_id=example_id,
            strict=True
        )
    except NotFoundError:
        await callback.answer("Не найдено", show_alert=True)
        return
    except ServiceError as exc:
        logger.error("handle_example_callback(): %s", exc, exc_info=True)
        await callback.answer("Ошибка при загрузке", show_alert=True)
        return

    await send_or_edit(callback, format_example_message(payload))

```

---
### Пока не понял
⚠️ Один нюанс, который надо зафиксировать рядом с шаблоном

В handle_example_message() мы вызываем get_by_telegram_id(..., strict=False) и получаем Optional.

Значит:
- либо format_example_message() умеет обрабатывать None
- либо в хендлере добавляется простой UX-guard:

if payload is None:
    await message.answer("Пока нет данных.")
    return

Канон: UX-guard — это handler responsibility ✅

---