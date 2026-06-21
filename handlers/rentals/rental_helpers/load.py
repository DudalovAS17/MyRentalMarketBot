from typing import TypeVar
from collections.abc import Awaitable, Callable
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from utils.functions import send_or_edit, abort_rent_flow
from utils.errors import ServiceError

T = TypeVar("T")

async def load_item_or_abort(
        event: CallbackQuery | Message,
        state: FSMContext,
        loader: Callable[[int], Awaitable[T | None]],
        entity_id: int | None,
        invalid_id_text: str,
        load_error_text: str,
        not_found_text: str,
        rent_ui_message_id: int | None = None,
) -> T | None:
    """Загрузить item для rent-flow или корректно завершить/оставить сценарий"""

    if entity_id is None:
        await abort_rent_flow(event, state, invalid_id_text, rent_ui_message_id=rent_ui_message_id)
        return None

    try:
        entity = await loader(entity_id)
    except ServiceError:
        await send_or_edit(event, load_error_text)
        return None

    if entity is None:
        await abort_rent_flow(event, state, not_found_text, rent_ui_message_id=rent_ui_message_id)
        return None

    return entity