from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from utils.functions import send_or_edit, abort_rent_flow
from utils.errors import ServiceError, ValidationError
from schemas.rental import RentalCreateDraft


async def load_item(
        callback: CallbackQuery,
        state: FSMContext,
        loader, # : Callable[[int], Awaitable[T | None]],
        entity_id: int | None,
        invalid_id_text: str,
        load_error_text: str,
        not_found_text: str,
        rent_ui_message_id: int | None = None,
): #  -> list[T] | None:

    if entity_id is None:
        # Fatal: некорректная кнопка | нет item_id → чистим FSM и выходим
        if rent_ui_message_id:
            await abort_rent_flow(callback, state, invalid_id_text, rent_ui_message_id=rent_ui_message_id)
        else:
            await abort_rent_flow(callback, state, invalid_id_text)
        return None

    try:
        entity = await loader(entity_id)
    except ServiceError:
        # Recoverable: сервис/БД временно недоступны, FSM не трогаем (→ остаёмся в этом шаге)
        await send_or_edit(callback, load_error_text)
        return None # show_my_rentals()

    if entity is None:
        # Fatal: объявления нет → чистим FSM
        if rent_ui_message_id:
            await abort_rent_flow(callback, state, not_found_text, rent_ui_message_id=rent_ui_message_id)
        else:
            await abort_rent_flow(callback, state, not_found_text)
        return None # show_my_rentals()

    return entity


async def get_rent_end_date_context_or_abort(
    callback: CallbackQuery,
    state: FSMContext,
    no_start_rent_date: str,
) -> tuple[RentalCreateDraft, int | None, str] | None:

    data = await state.get_data()
    rent_ui_message_id = data.get("rent_ui_message_id")
    draft_dict = data.get("rent_draft") or {}

    try:
        draft = RentalCreateDraft.model_validate(draft_dict)
    except ValidationError:
        # Fatal: draft повреждён → завершаем flow
        err_text = "❌ Данные аренды повреждены. Начните заново."
        await abort_rent_flow(callback, state, err_text, rent_ui_message_id=rent_ui_message_id)
        return None

    start_date_str = draft.start_date
    if not start_date_str:
        # Fatal: нет start_date → завершаем flow
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
        # Fatal: draft повреждён → завершаем flow
        await abort_rent_flow(callback, state, data_err, rent_ui_message_id)
        return None

    if not (draft.item_id and draft.owner_id and draft.renter_id and draft.start_date and draft.end_date):
        # Fatal: не хватает данных → завершаем flow
        await abort_rent_flow(callback, state, not_all_data_err, rent_ui_message_id=rent_ui_message_id)
        return None

    return draft, rent_ui_message_id