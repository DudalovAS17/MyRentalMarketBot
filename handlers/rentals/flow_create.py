from aiogram import F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from .router import rental_router

from handlers.rentals import create_helpers as ch
from services.item_service import ItemService
from services.rental_service import RentalService
from services.notif_service import NotificationService

from states.rental import RentalCreateStates
from schemas.rental import RentalCreate, RentalCreateDraft
from keyboards.common import build_rent_confirmation_keyboard
from utils.functions import send_or_edit, render_rent_ui, abort_rent_flow
from utils.errors import ServiceError, ValidationError
from utils.callbacks import CONFIRM_RENT_CB, CANCEL_RENT_FLOW_CB, RENT_ITEM_CB, RENT_PERIOD_CB


@rental_router.callback_query(F.data.startswith(RENT_ITEM_CB))
async def start_rent_process(callback: CallbackQuery, state: FSMContext, item_service: ItemService, rental_service: RentalService, user) -> None:
    """Старт FSM: Создание запроса аренды"""
    await callback.answer()

    item = await ch.load_item_or_abort(callback, state, item_service.get_item_by_id,
                                       ch.parse_rent_item_id(callback.data), invalid_id_text=ch.not_item_id,
                                       load_error_text=ch.serv_item_err,
                                       not_found_text=ch.not_item)
    if item is None:
        return

    if await ch.abort_if_item_unavailable(callback, rental_service, item):
        return # вещь недоступна

    draft = RentalCreateDraft(
        item_id=item.id,
        client_name=user.full_name,
        client_phone=user.phone,
    )

    await state.clear()
    await state.update_data(
        rent_draft=draft.model_dump(mode="json"),
        rent_ui_message_id=None,
    )

    # отправляем отдельное сообщение - “экран аренды”
    sent = await callback.message.answer(
        ch.format_rent_period_text(item), # format_start_date_rent_text
        reply_markup=ch.build_rent_period_keyboard(item.id), # build_start_date_keyboard
        parse_mode="HTML"
    )

    await state.update_data(rent_ui_message_id=sent.message_id)
    await state.set_state(RentalCreateStates.period)

@rental_router.callback_query(RentalCreateStates.period, F.data.startswith(RENT_PERIOD_CB))
async def process_fixed_period(
    callback: CallbackQuery,
    state: FSMContext,
    item_service: ItemService,
    rental_service: RentalService,
) -> None:
    """FSM: Обработать выбор одного из четырёх фиксированных диапазонов аренды."""
    await callback.answer()

    period_code = ch.parse_rent_period_code(callback.data) # (callback, state)
    if period_code is None:
        await callback.answer("Некорректный срок аренды.", show_alert=True)
        return

    # проверь
    draft_ctx = await ch.get_rent_draft_context_or_abort(callback, state, ch.rental_data_err, ch.not_all_rental_data_err)  # get_rent_draft_from_state?
    if draft_ctx is None:
        # await abort_rent_flow(callback, state, ch.rental_data_err, rent_ui_message_id)
        return
    draft, rent_ui_message_id = draft_ctx

    item = await ch.load_item_or_abort(
        callback, state, item_service.get_item_by_id, draft.item_id, invalid_id_text=ch.not_item_for_rental,
        load_error_text=ch.serv_item_err, not_found_text=ch.not_item, rent_ui_message_id=rent_ui_message_id,
    )
    if item is None:
        return

    if await ch.abort_if_item_unavailable(callback, rental_service, item):
        return # вещь недоступна

    # сохраняем period_text, total_price в draft (Считаем итоговую стоимость)
    period_text = ch.PERIOD_LABELS[period_code]

    period_price = ch.calculate_price_for_fixed_period_total(item.price, period_code, item.price_text)
    await ch.store_fixed_period_choice_and_price(state, draft, period_text, period_price)
    # в store_rent_start_date_or_abort еще были: ch.rental_data_err, ch.not_item_for_rental

    await render_rent_ui(
        callback,
        state,
        ch.format_rent_details_request_text(item, period_text),
        ch.build_rent_cancel_keyboard(item.id),
        rent_ui_message_id,
    )
    await state.set_state(RentalCreateStates.comment)

@rental_router.message(RentalCreateStates.comment)
async def process_rent_details_message(
    message: Message,
    state: FSMContext,
    item_service: ItemService,
    rental_service: RentalService,
) -> None:
    """FSM: Обработать сообщение клиента (количеством дней, датой и комментарий)."""

    parsed = ch.parse_rent_details_message(message.text)
    if parsed is None:
        await message.answer(
            "⚠️ Не удалось разобрать сообщение. Отправьте в формате:\n"
            "<code>3 - 25.06.2026 - Нужна доставка вечером</code>",
            parse_mode="HTML",
        )
        return

    days, needed_by_date, client_comment = parsed

    draft_ctx = await ch.get_rent_draft_context_or_abort(message, state, ch.rental_data_err, ch.not_all_rental_data_err)
    if draft_ctx is None:
        return
    draft, rent_ui_message_id = draft_ctx

    item = await ch.load_item_or_abort(
        message, state, item_service.get_item_by_id, draft.item_id, invalid_id_text=ch.not_item_for_rental,
        load_error_text=ch.serv_item_err, not_found_text=ch.not_item, rent_ui_message_id=rent_ui_message_id,
    )
    if item is None:
        return

    if await ch.abort_if_item_unavailable(message, rental_service, item):
        return

    await ch.store_rent_details_message(state, draft, client_comment) # format_fixed_period_confirmation_text

    total_price = draft.total_price
    rental_period_text = f"{draft.rental_period_text}; указано: {days} дн., товар нужен к {needed_by_date}"

    await render_rent_ui(
        message,
        state,
        ch.format_rent_confirmation_text(item, rental_period_text, total_price, client_comment),
        build_rent_confirmation_keyboard(),
        rent_ui_message_id,
    )
    await state.set_state(RentalCreateStates.confirmation)

@rental_router.callback_query(RentalCreateStates.confirmation, F.data == CONFIRM_RENT_CB)
async def confirm_rent(
    callback: CallbackQuery,
    state: FSMContext,
    rental_service: RentalService,
    item_service: ItemService,
    notification_service: NotificationService,
    admin_ids: list[int], # это ок, что тут id админов?
    user,
) -> None:
    """FSM: Создать заявку на аренду - показать экран успеха - уведомить владельца."""
    await callback.answer()

    confirm_ctx = await ch.get_rent_draft_context_or_abort(callback, state, ch.rental_data_err,
                                                           ch.not_all_rental_data_err)
    if confirm_ctx is None:
        return
    draft, rent_ui_message_id = confirm_ctx

    item = await ch.load_item_or_abort(callback, state, item_service.get_item_by_id, draft.item_id,
                                       invalid_id_text=ch.not_item_for_rental, load_error_text=ch.serv_item_err,
                                       not_found_text=ch.not_item, rent_ui_message_id=rent_ui_message_id)
    if item is None:
        return

    if await ch.abort_if_item_unavailable(callback, rental_service, item): # draft.item_id
        return # вещь занята

    try:
        payload = RentalCreate(
            item_id=draft.item_id,
            user_id=user.id, # берём из контекста (middleware), не доверяем state на 100%
            rental_period_text=draft.rental_period_text,
            #quantity=draft.quantity or 1,
            total_price=draft.total_price,
            client_name=draft.client_name,
            client_phone=draft.client_phone,
            client_comment=draft.client_comment,
        )
    except ValidationError:
        await abort_rent_flow(callback, state, ch.rental_data_err, rent_ui_message_id)
        return

    # Создаём аренду
    try:
        rental = await rental_service.create(payload)
    except ServiceError:
        await send_or_edit(callback, "❌ Не удалось создать заявку. Попробуйте позже.")
        return

    # уведомление клиента/админа о новой заявке
    rental_details = await rental_service.get_rental_details(rental.id, user.id)
    if rental_details is not None:
        await notification_service.notify_user_rental_created(user.telegram_id, rental_details)
        await notification_service.notify_admins_new_rental(admin_ids, rental_details)

    text = ch.build_success_text(item, draft.rental_period_text, draft.total_price)
    await render_rent_ui(callback, state, text, ch.build_rent_success_keyboard(), rent_ui_message_id)
    await state.clear()

@rental_router.callback_query(F.data == CANCEL_RENT_FLOW_CB)
async def cancel_rent_flow(callback: CallbackQuery, state: FSMContext) -> None:
    """FSM: Отменить rent-flow и очистить FSM"""
    await callback.answer()

    data = await state.get_data()
    rent_ui_message_id = data.get("rent_ui_message_id")
    draft_dict = data.get("rent_draft") or {}
    item_id = draft_dict.get("item_id")

    await render_rent_ui(callback, state, ch.cancel_rent, ch.build_rent_cancel_keyboard(item_id), rent_ui_message_id)

    await state.clear()


""" Иная логика ввода дат:
    ask_custom_dates - Попросить клиента ввести свой диапазон дат одним сообщением - CUSTOM_RENT_DATES_CB
    process_custom_dates - Обработать ручной ввод дат и показать подтверждение заявки.
    ignore_callback - No-op обработчик для служебных кнопок-заголовков - F.data == IGNORE_CB
"""