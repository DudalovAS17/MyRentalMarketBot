from decimal import Decimal
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from utils.functions import abort_rent_flow
from utils.errors import ValidationError
from schemas.rental import RentalCreateDraft


async def save_rent_draft(state: FSMContext, draft: RentalCreateDraft) -> None:
    """Сохранить FSM draft."""
    await state.update_data(rent_draft=draft.model_dump(mode="json"))

async def get_rent_confirm_context_or_abort(
        event: CallbackQuery | Message,
        state: FSMContext,
        data_err: str, # rent_data_err
        not_all_data_err: str # invalid_id_text
) -> tuple[RentalCreateDraft, int | None] | None:
    """Восстановить FSM draft и id сообщения rent-ui."""

    data = await state.get_data()
    rent_ui_message_id = data.get("rent_ui_message_id")
    draft_dict = data.get("rent_draft") or {}

    try:
        draft = RentalCreateDraft.model_validate(draft_dict)
    except ValidationError: # PydanticValidationError
        await abort_rent_flow(event, state, data_err, rent_ui_message_id) # rent_data_err
        return None

    if not (draft.item_id and draft.rental_period_text): # is None:
        await abort_rent_flow(event, state, not_all_data_err, rent_ui_message_id=rent_ui_message_id) # invalid_id_text
        return None

    return draft, rent_ui_message_id

async def store_fixed_period_choice_and_price(
    state: FSMContext,
    draft: RentalCreateDraft,
    period_text: str,
    total_price: Decimal | None,
) -> None:
    """Запись в draft: фиксированный диапазон аренды и цену."""
    draft.rental_period_text = period_text
    draft.total_price = total_price
    await save_rent_draft(state, draft)