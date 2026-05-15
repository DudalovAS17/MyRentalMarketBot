from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from decimal import Decimal

from utils.functions import abort_rent_flow
from utils.errors import ValidationError
from schemas.rental import RentalCreateDraft
from schemas.item import ItemOut

async def store_rent_start_date_or_abort(
    callback: CallbackQuery,
    state: FSMContext,
    start_str: str,
    rent_data_err: str,
    invalid_id_text: str,
) -> tuple[int, int | None] | None:
    """Записать дату начала аренды в rental draft или завершить rent-flow"""

    data = await state.get_data()
    rent_ui_message_id = data.get("rent_ui_message_id")
    rent_draft_dict = data.get("rent_draft") or {}

    try:
        draft = RentalCreateDraft.model_validate(rent_draft_dict)
    except ValidationError:
        await abort_rent_flow(callback, state, rent_data_err, rent_ui_message_id=rent_ui_message_id)
        return None

    if draft.item_id is None:
        await abort_rent_flow(callback, state, invalid_id_text, rent_ui_message_id=rent_ui_message_id)
        return None

    draft.start_date = start_str
    await state.update_data(rent_draft=draft.model_dump(mode="json"))

    return draft.item_id, rent_ui_message_id


async def store_rent_end_date_and_amounts(
    state: FSMContext,
    draft: RentalCreateDraft,
    end_str: str,
    item: ItemOut,
    total_price: Decimal,
) -> None:
    """Запись в draft: дата окончания, цена, депозит-залог"""

    draft.end_date = end_str
    draft.total_price = total_price

    if draft.deposit_amount is None and item.deposit is not None:
        draft.deposit_amount = item.deposit

    await state.update_data(rent_draft=draft.model_dump(mode="json"))