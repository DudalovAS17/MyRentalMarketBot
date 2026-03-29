from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from decimal import Decimal

from handlers.rentals import create_helpers as ch

from utils.functions import abort_rent_flow
from utils.errors import ValidationError
from schemas.rental import RentalCreateDraft


async def store_rent_start_date_or_abort(
    callback: CallbackQuery,
    state: FSMContext,
    start_str: str,
    rent_data_err: str,
    invalid_id_text: str,
) -> tuple[int, int | None] | None:

    data = await state.get_data()
    rent_ui_message_id = data.get("rent_ui_message_id")
    rent_draft_dict = data.get("rent_draft") or {}

    try:
        draft = RentalCreateDraft.model_validate(rent_draft_dict)
    except ValidationError:
        # Fatal: draft повреждён → завершаем flow
        await abort_rent_flow(callback, state, rent_data_err, rent_ui_message_id=rent_ui_message_id)
        return None

    if not draft.item_id:
        # Fatal: некорректная кнопка | нет item_id → чистим FSM и выходим
        await abort_rent_flow(callback, state, invalid_id_text, rent_ui_message_id=rent_ui_message_id)
        return None

    draft.start_date = start_str # В draft храним строку. Переведем в datetime внутри confirm-функции
    await state.update_data(rent_draft=draft.model_dump(mode="json"))

    return draft.item_id, rent_ui_message_id

async def store_rent_end_date_and_amounts(
    state: FSMContext,
    draft: RentalCreateDraft,
    end_str: str,
    item,
    days: int,
) -> tuple[Decimal, Decimal]:
    """Запись в draft: дата окончания, цена, депозит-залог"""
    # Считаем итоговую стоимость
    price_per_day, total_price = ch.calculate_total_rent_price(item.price, days)

    # Обновляем draft
    draft.end_date = end_str
    draft.total_price = total_price

    # deposit_amount уже может быть проставлен на старте из item.deposit
    if draft.deposit_amount is None and getattr(item, "deposit", None) is not None:
        draft.deposit_amount = item.deposit

    await state.update_data(rent_draft=draft.model_dump(mode="json"))

    return price_per_day, total_price