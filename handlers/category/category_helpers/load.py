from collections.abc import Awaitable, Callable
from typing import TypeVar
from aiogram.types import CallbackQuery

from utils.functions import send_or_edit
from utils.errors import ServiceError

T = TypeVar("T")

async def resolve_entity(
        callback: CallbackQuery,
        loader: Callable[[int], Awaitable[T | None]],
        entity_id: int | None,
        invalid_id_text: str,
        load_error_text: str,
        not_found_text: str,
) -> T | None:
    """Загрузить сущность или показать UX-ошибку при невозможности продолжить flow"""
    if entity_id is None:
        await send_or_edit(callback, invalid_id_text)
        return None

    try:
        entity = await loader(entity_id)
    except ServiceError:
        await send_or_edit(callback, load_error_text)
        return None

    if entity is None:
        await callback.answer(not_found_text, show_alert=True)
        return None

    return entity

async def load_entity_or_notify(
        callback: CallbackQuery,
        loader: Callable[[int], Awaitable[T | None]],
        entity_id: int | None,
        invalid_id_text: str,
        load_error_text: str,
        not_found_text: str
)  -> list[T] | None:

    if entity_id is None:
        await send_or_edit(callback, invalid_id_text)
        return None

    try:
        entity = await loader(entity_id)
    except ServiceError:
        await send_or_edit(callback, load_error_text)
        return None

    if entity is None:
        await send_or_edit(callback, not_found_text)
        return None

    return entity
