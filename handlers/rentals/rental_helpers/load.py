from typing import TypeVar
from collections.abc import Awaitable, Callable
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from utils.functions import send_or_edit, abort_rent_flow
from utils.errors import ServiceError, ValidationError
from schemas.rental import RentalCreateDraft

T = TypeVar("T")

async def load_item_or_abort(
        callback: CallbackQuery,
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
        await abort_rent_flow(callback, state, invalid_id_text, rent_ui_message_id=rent_ui_message_id)
        return None

    try:
        entity = await loader(entity_id)
    except ServiceError:
        await send_or_edit(callback, load_error_text)
        return None

    if entity is None:
        await abort_rent_flow(callback, state, not_found_text, rent_ui_message_id=rent_ui_message_id)
        return None

    return entity


async def get_rent_end_date_context_or_abort(
        callback: CallbackQuery,
        state: FSMContext,
        data_err: str,
        no_start_rent_date: str
) -> tuple[RentalCreateDraft, int | None, str] | None:
    """Восстановить context для шага-выбора даты окончания аренды"""

    data = await state.get_data()
    rent_ui_message_id = data.get("rent_ui_message_id")
    draft_dict = data.get("rent_draft") or {}

    try:
        draft = RentalCreateDraft.model_validate(draft_dict)
    except ValidationError:
        await abort_rent_flow(callback, state, data_err, rent_ui_message_id=rent_ui_message_id)
        return None

    start_date_str = draft.start_date
    if not start_date_str:
        await abort_rent_flow(callback, state, no_start_rent_date, rent_ui_message_id=rent_ui_message_id)
        return None

    return draft, rent_ui_message_id, start_date_str


async def get_rent_confirm_context_or_abort(
        callback: CallbackQuery,
        state: FSMContext,
        data_err: str,
        not_all_data_err: str
) -> tuple[RentalCreateDraft, int | None] | None:
    """Поднять финальный context из FSM"""

    data = await state.get_data()
    rent_ui_message_id = data.get("rent_ui_message_id")
    draft_dict = data.get("rent_draft") or {}

    try:
        draft = RentalCreateDraft.model_validate(draft_dict)
    except ValidationError:
        await abort_rent_flow(callback, state, data_err, rent_ui_message_id)
        return None

    if not (draft.item_id and draft.owner_id and draft.renter_id and draft.start_date and draft.end_date):
        await abort_rent_flow(callback, state, not_all_data_err, rent_ui_message_id=rent_ui_message_id)
        return None

    return draft, rent_ui_message_id