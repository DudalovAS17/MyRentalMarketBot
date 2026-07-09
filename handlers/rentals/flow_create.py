from aiogram import F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from pydantic import ValidationError as PydanticValidationError

from .router import rental_router

from handlers.rentals import create_helpers as ch
from handlers.admin.admin_helpers.keyboard import get_admin_new_rental_notification_keyboard
from services.item_service import ItemService
from services.rental_service import RentalService
from services.notif_service import NotificationService

from states.rental import RentalCreateStates
from schemas.rental import RentalCreate, RentalCreateDraft

from utils.functions import send_or_edit, render_rent_ui, abort_rent_flow
from utils.errors import ServiceError
from utils.callbacks import (CONFIRM_RENT_CB, CANCEL_RENT_FLOW_CB, RENT_ITEM_CB, RENT_PERIOD_CB, RENT_QUANTITY_CB,
                             RENT_DELIVERY_CB, RENT_BACK_CB, RENT_USE_PROFILE_NAME_CB, RENT_USE_PROFILE_PHONE_CB,
                             RENT_SKIP_COMMENT_CB) # , RENT_CHANGE_CB

# process_quantity:
# if await ch.abort_if_item_unavailable(callback, rental_service, item):
#    return # вещь недоступна


# ─────────────────────────── _Render (Показать шаг выбора X и перевести FSM в состояние X) ────────────────────────────
async def _render_quantity(event: CallbackQuery | Message, state: FSMContext, item, rent_ui_message_id: int | None) -> None:
    await render_rent_ui(event, state, ch.format_rent_quantity_text(item), ch.build_rent_quantity_keyboard(item.available_quantity), rent_ui_message_id)
    await state.set_state(RentalCreateStates.quantity)

async def _render_period(event: CallbackQuery | Message, state: FSMContext, item, rent_ui_message_id: int | None) -> None:
    await render_rent_ui(event, state, ch.format_rent_period_text(item), ch.build_rent_period_keyboard(), rent_ui_message_id)
    await state.set_state(RentalCreateStates.period)

async def _render_delivery(event: CallbackQuery | Message, state: FSMContext, item, draft: RentalCreateDraft, rent_ui_message_id: int | None) -> None:
    await render_rent_ui(event, state, ch.format_rent_delivery_text(item, draft), ch.build_rent_delivery_keyboard(), rent_ui_message_id)
    await state.set_state(RentalCreateStates.delivery_needed)

async def _render_name(event: CallbackQuery | Message, state: FSMContext, draft: RentalCreateDraft, rent_ui_message_id: int | None) -> None:
    prof_cb = RENT_USE_PROFILE_NAME_CB if draft.client_name else None
    await render_rent_ui(event, state, ch.format_rent_client_name_text(draft.client_name), ch.build_rent_contact_keyboard(prof_cb), rent_ui_message_id)
    await state.set_state(RentalCreateStates.client_name)

async def _render_phone(event: CallbackQuery | Message, state: FSMContext, draft: RentalCreateDraft, rent_ui_message_id: int | None) -> None:
    prof_cb = RENT_USE_PROFILE_PHONE_CB if draft.client_phone else None
    await render_rent_ui(event, state, ch.format_rent_client_phone_text(draft.client_phone), ch.build_rent_contact_keyboard(prof_cb), rent_ui_message_id)
    await state.set_state(RentalCreateStates.client_phone)

async def _render_comment(event: CallbackQuery | Message, state: FSMContext, draft: RentalCreateDraft, rent_ui_message_id: int | None) -> None:
    await render_rent_ui(event, state, ch.format_rent_comment_text(), ch.build_rent_comment_keyboard(), rent_ui_message_id)
    await state.set_state(RentalCreateStates.client_comment)

async def _render_confirmation(event: CallbackQuery | Message, state: FSMContext, item, draft: RentalCreateDraft, rent_ui_message_id: int | None) -> None:
    await render_rent_ui(event, state, ch.format_rent_confirmation_text(item, draft), ch.build_rent_confirmation_keyboard(), rent_ui_message_id)
    await state.set_state(RentalCreateStates.confirmation)


# ───────────────────────────────────────────── Rental FSM ─────────────────────────────────────────────────────────────
async def load_context(event: CallbackQuery | Message, state: FSMContext, item_service: ItemService):
    """Загрузить draft и товар для текущего шага rent-flow или аварийно остановить сценарий."""
    ctx = await ch.get_rent_draft_context_or_abort(event, state, ch.rental_data_err, ch.not_all_rental_data_err)
    if ctx is None:
        return None
    draft, rent_ui_message_id = ctx

    item = await ch.load_item_or_abort(event, state, item_service.get_item_by_id, draft.item_id,
                                       invalid_id_text=ch.not_item_id, load_error_text=ch.serv_item_err,
                                       not_found_text=ch.not_item, rent_ui_message_id=rent_ui_message_id)
    if item is None:
        return None

    return draft, rent_ui_message_id, item


@rental_router.callback_query(F.data.startswith(RENT_ITEM_CB))
async def start_rent_process(callback: CallbackQuery, state: FSMContext, item_service: ItemService, rental_service: RentalService, user) -> None:
    """Старт FSM: создание структурированной заявки на аренду."""
    await callback.answer()

    item = await ch.load_item_or_abort(callback, state, item_service.get_item_by_id,
                                       ch.parse_rent_item_id(callback.data), invalid_id_text=ch.not_item_id,
                                       load_error_text=ch.serv_item_err, not_found_text=ch.not_item)
    if item is None:
        return

    if await ch.abort_if_item_unavailable(callback, rental_service, item):
        return # вещь недоступна

    draft = RentalCreateDraft(item_id=item.id, quantity=1, client_name=user.full_name, client_phone=user.phone)

    await state.clear()
    await state.update_data(
        rent_draft=draft.model_dump(mode="json"),
        rent_ui_message_id=None
    )

    await _render_quantity(callback, state, item, rent_ui_message_id=None)

    # # отправляем отдельное сообщение - “экран аренды”
    # sent = await callback.message.answer(
    #     ch.format_rent_quantity_text(item),
    #     reply_markup=ch.build_rent_quantity_keyboard(item.available_quantity),
    #     parse_mode="HTML"
    # )
    #
    # await state.update_data(rent_ui_message_id=sent.message_id)
    # await state.set_state(RentalCreateStates.quantity)


@rental_router.callback_query(RentalCreateStates.quantity, F.data.startswith(RENT_QUANTITY_CB))
async def process_quantity_button(callback: CallbackQuery, state: FSMContext, item_service: ItemService) -> None:
    """Обработать callback выбора количества и перейти к сроку аренды."""

    ctx = await load_context(callback, state, item_service)
    if ctx is None:
        return
    draft, rent_ui_message_id, item = ctx

    if (callback.data or "").endswith("manual"):
        await callback.answer("Введите количество сообщением.", show_alert=True)
        return

    await callback.answer()

    quantity = ch.parse_rent_quantity_code(callback.data)
    if quantity is None or not ch.is_quantity_available(quantity, item.available_quantity):
        await callback.answer("Некорректное количество.", show_alert=True)
        return

    draft.quantity = quantity
    await ch.save_rent_draft(state, draft)

    await _render_period(callback, state, item, rent_ui_message_id)

@rental_router.message(RentalCreateStates.quantity)
async def process_quantity_message(message: Message, state: FSMContext, item_service: ItemService) -> None:
    """Обработать ручной ввод количества и перейти к сроку аренды."""
    ctx = await load_context(message, state, item_service)
    if ctx is None:
        return
    draft, rent_ui_message_id, item = ctx

    quantity = ch.parse_positive_int(message.text)
    if quantity is None or not ch.is_quantity_available(quantity, item.available_quantity):
        await message.answer(f"⚠️ Введите число от 1 до {item.available_quantity}.")
        return

    draft.quantity = quantity
    await ch.save_rent_draft(state, draft)

    await _render_period(message, state, item, rent_ui_message_id)


@rental_router.callback_query(RentalCreateStates.period, F.data.startswith(RENT_PERIOD_CB))
async def process_fixed_period(callback: CallbackQuery, state: FSMContext, item_service: ItemService, rental_service: RentalService) -> None:
    """Обработать выбор фиксированного срока аренды и перейти к доставке."""
    await callback.answer()

    ctx = await load_context(callback, state, item_service)
    if ctx is None:
        return
    draft, rent_ui_message_id, item = ctx

    if await ch.abort_if_item_unavailable(callback, rental_service, item):
        return

    period_code = ch.parse_rent_period_code(callback.data)
    if period_code is None:
        await callback.answer("Некорректный срок аренды.", show_alert=True)
        return

    # сохраняем period_text, total_price в draft (Считаем итоговую стоимость)
    draft.rental_period_text = ch.PERIOD_LABELS[period_code]
    draft.total_price = ch.calculate_price_for_fixed_period_total(item.price, period_code, item.price_text)
    await ch.save_rent_draft(state, draft)

    await _render_delivery(callback, state, item, draft, rent_ui_message_id)


@rental_router.callback_query(RentalCreateStates.delivery_needed, F.data.startswith(RENT_DELIVERY_CB))
async def process_delivery_needed(callback: CallbackQuery, state: FSMContext, item_service: ItemService) -> None:
    """Обработать выбор доставки и запросить адрес при необходимости."""
    await callback.answer()

    ctx = await load_context(callback, state, item_service)
    if ctx is None:
        return
    draft, rent_ui_message_id, item = ctx

    delivery_needed = ch.parse_delivery_choice(callback.data)
    if delivery_needed is None:
        await callback.answer("Некорректный выбор доставки.", show_alert=True)
        return

    draft.delivery_needed = delivery_needed
    draft.delivery_address = None
    await ch.save_rent_draft(state, draft)

    if delivery_needed:
        await render_rent_ui(callback, state, ch.format_rent_delivery_address_text(), ch.build_rent_step_keyboard(), rent_ui_message_id)
        await state.set_state(RentalCreateStates.delivery_address)
    else:
        await _render_name(callback, state, draft, rent_ui_message_id)


@rental_router.message(RentalCreateStates.delivery_address)
async def process_delivery_address(message: Message, state: FSMContext, item_service: ItemService) -> None:
    """Сохранить адрес доставки и перейти к контактному имени."""
    ctx = await load_context(message, state, item_service)
    if ctx is None:
        return
    draft, rent_ui_message_id, item = ctx

    address = (message.text or "").strip()
    if len(address) < 5:
        await message.answer("⚠️ Укажите адрес доставки подробнее.")
        return

    draft.delivery_address = address[:1000]
    await ch.save_rent_draft(state, draft)

    await _render_name(message, state, draft, rent_ui_message_id)


@rental_router.callback_query(RentalCreateStates.client_name, F.data == RENT_USE_PROFILE_NAME_CB)
async def use_profile_name(callback: CallbackQuery, state: FSMContext, item_service: ItemService) -> None:
    """Подтвердить имя из профиля и перейти к телефону."""
    await callback.answer()

    ctx = await load_context(callback, state, item_service)
    if ctx is None:
        return
    draft, rent_ui_message_id, _ = ctx

    if not draft.client_name:
        await callback.answer("В профиле нет имени.", show_alert=True)
        return

    await _render_phone(callback, state, draft, rent_ui_message_id)

@rental_router.message(RentalCreateStates.client_name)
async def process_client_name(message: Message, state: FSMContext, item_service: ItemService) -> None:
    """Сохранить введённое имя клиента и перейти к телефону."""
    ctx = await load_context(message, state, item_service)
    if ctx is None:
        return
    draft, rent_ui_message_id, _ = ctx

    name = (message.text or "").strip()
    if len(name) < 2:
        await message.answer("⚠️ Введите имя минимум из 2 символов.")
        return

    draft.client_name = name[:150]
    await ch.save_rent_draft(state, draft)

    await _render_phone(message, state, draft, rent_ui_message_id)


@rental_router.callback_query(RentalCreateStates.client_phone, F.data == RENT_USE_PROFILE_PHONE_CB)
async def use_profile_phone(callback: CallbackQuery, state: FSMContext, item_service: ItemService) -> None:
    """Подтвердить телефон из профиля и перейти к комментарию."""
    await callback.answer()

    ctx = await load_context(callback, state, item_service)
    if ctx is None:
        return
    draft, rent_ui_message_id, _ = ctx

    if not draft.client_phone:
        await callback.answer("В профиле нет телефона.", show_alert=True)
        return

    await _render_comment(callback, state, draft, rent_ui_message_id)

@rental_router.message(RentalCreateStates.client_phone)
async def process_client_phone(message: Message, state: FSMContext, item_service: ItemService) -> None:
    """Сохранить введённый телефон клиента и перейти к комментарию."""
    ctx = await load_context(message, state, item_service)
    if ctx is None:
        return
    draft, rent_ui_message_id, _ = ctx

    phone = ch.normalize_phone(message.text)
    if phone is None:
        await message.answer("⚠️ Введите телефон в формате +7XXXXXXXXXX или похожем.")
        return

    draft.client_phone = phone
    await ch.save_rent_draft(state, draft)

    await _render_comment(message, state, draft, rent_ui_message_id)


@rental_router.callback_query(RentalCreateStates.client_comment, F.data == RENT_SKIP_COMMENT_CB)
async def skip_comment(callback: CallbackQuery, state: FSMContext, item_service: ItemService) -> None:
    """Пропустить комментарий и показать экран подтверждения."""
    await callback.answer()

    ctx = await load_context(callback, state, item_service)
    if ctx is None:
        return
    draft, rent_ui_message_id, item = ctx

    draft.client_comment = None
    await ch.save_rent_draft(state, draft)

    await _render_confirmation(callback, state, item, draft, rent_ui_message_id)

@rental_router.message(RentalCreateStates.client_comment)
async def process_comment(message: Message, state: FSMContext, item_service: ItemService) -> None:
    """Сохранить комментарий клиента и показать экран подтверждения."""
    ctx = await load_context(message, state, item_service)
    if ctx is None:
        return
    draft, rent_ui_message_id, item = ctx

    draft.client_comment = (message.text or "").strip()[:2000] or None
    await ch.save_rent_draft(state, draft)

    await _render_confirmation(message, state, item, draft, rent_ui_message_id)


# @rental_router.callback_query(RentalCreateStates.confirmation, F.data == RENT_CHANGE_CB)
# async def change_request(callback: CallbackQuery, state: FSMContext, item_service: ItemService) -> None:
#     """Показать меню выбора конкретного поля заявки для изменения."""
#     await callback.answer()
#
#     ctx = await load_context(callback, state, item_service)
#     if ctx is None:
#         return
#     draft, rent_ui_message_id, item = ctx
#
#     await callback.answer("Изменение заявки пока не входит в MVP.", show_alert=True)
#     await _render_confirmation(callback, state, item, draft, rent_ui_message_id)


@rental_router.callback_query(RentalCreateStates.confirmation, F.data == CONFIRM_RENT_CB)
async def confirm_rent(
        callback: CallbackQuery,
        state: FSMContext,
        rental_service: RentalService,
        item_service: ItemService,
        notification_service: NotificationService,
        admin_ids: list[int], # это ок, что тут id админов?
        user
) -> None:
    """FSM: Создать заявку на аренду - показать экран успеха - уведомить владельца."""
    await callback.answer()

    ctx = await load_context(callback, state, item_service)
    if ctx is None:
        return
    draft, rent_ui_message_id, item = ctx

    if await ch.abort_if_item_unavailable(callback, rental_service, item):
        return

    if not ch.is_rent_draft_complete(draft):
        await callback.answer("Не все поля заявки заполнены.", show_alert=True)
        return

    try:
        payload = RentalCreate(
            item_id=draft.item_id,
            user_id=user.id, # берём из контекста (middleware), не доверяем state на 100%
            rental_period_text=draft.rental_period_text,
            quantity=draft.quantity or 1,
            total_price=draft.total_price,
            delivery_needed=bool(draft.delivery_needed),
            delivery_address=draft.delivery_address if draft.delivery_needed else None,
            client_name=draft.client_name,
            client_phone=draft.client_phone,
            client_comment=draft.client_comment,
        )
    except PydanticValidationError:
        await abort_rent_flow(callback, state, ch.rental_data_err, rent_ui_message_id)
        return

    # Создаём аренду
    try:
        rental = await rental_service.create(payload, item=item)
    except ServiceError:
        await send_or_edit(callback, "❌ Не удалось создать заявку. Попробуйте позже.")
        return

    # уведомление клиента/админа о новой заявке
    rental_details = await rental_service.get_rental_details(rental.id, user.id)
    if rental_details is not None:
        await notification_service.notify_user_rental_created(user.telegram_id, rental_details)
        await notification_service.notify_admins_new_rental(
            admin_ids,
            rental_details,
            reply_markup=get_admin_new_rental_notification_keyboard(rental.id, user.telegram_id)
        )

    await render_rent_ui(callback, state, ch.build_success_text(item, draft), ch.build_rent_success_keyboard(), rent_ui_message_id)
    await state.clear()


@rental_router.callback_query(F.data == RENT_BACK_CB)
async def back_rent_flow(callback: CallbackQuery, state: FSMContext, item_service: ItemService) -> None:

    await callback.answer()

    current = await state.get_state()

    ctx = await load_context(callback, state, item_service)
    if ctx is None:
        return
    draft, rent_ui_message_id, item = ctx

    if current == RentalCreateStates.period.state:
        await _render_quantity(callback, state, item, rent_ui_message_id)
    elif current == RentalCreateStates.delivery_needed.state:
        await _render_period(callback, state, item, rent_ui_message_id)
    elif current == RentalCreateStates.delivery_address.state:
        await _render_delivery(callback, state, item, draft, rent_ui_message_id)
    elif current == RentalCreateStates.client_name.state:
        await _render_delivery(callback, state, item, draft, rent_ui_message_id)
    elif current == RentalCreateStates.client_phone.state:
        await _render_name(callback, state, draft, rent_ui_message_id)
    elif current == RentalCreateStates.client_comment.state:
        await _render_phone(callback, state, draft, rent_ui_message_id)
    elif current == RentalCreateStates.confirmation.state:
        await _render_comment(callback, state, draft, rent_ui_message_id)


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