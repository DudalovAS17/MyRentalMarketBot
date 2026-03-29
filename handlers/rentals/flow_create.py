import logging
from aiogram import F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from decimal import Decimal

from .router import rental_router

from handlers.rentals import create_helpers as ch
from services.item_service import ItemService
from services.user_service import UserService
from services.rental_service import RentalService
from services.notif_service import NotificationService

from states.rental import RentStates
from utils.functions import send_or_edit, render_rent_ui, abort_rent_flow
from utils.errors import ServiceError, ValidationError
from schemas.rental import RentalCreate, RentalCreateDraft
from keyboards.rental_kb import build_rent_end_date_keyboard, build_rent_confirmation_keyboard
from utils.callbacks import RENT_ITEM_CB, START_DATE_CB, END_DATE_CB, CONFIRM_RENT_CB, CANCEL_RENT_FLOW_CB, IGNORE_CB

logger = logging.getLogger(__name__)


@rental_router.callback_query(F.data.startswith(RENT_ITEM_CB))
#@rental_router.callback_query(F.data.startswith("back_to_start_date:"))
async def start_rent_process(callback: CallbackQuery, state: FSMContext, item_service: ItemService, rental_service: RentalService, user) -> None:
    """Старт процесса аренды"""
    await callback.answer()

    # Получаем товар
    item = await ch.load_item(callback, state, item_service.get_item_by_id,
                                            ch.parse_rent_item_id(callback.data),
                                            invalid_id_text=ch.not_item_id, load_error_text=ch.serv_item_err,
                                            not_found_text=ch.not_item) # parse_callback(callback.data, RENT_ITEM_CB)
    if item is None:
        return

    logger.info(f"Пользователь {user.id} начинает процесс аренды для товара {item.id}")

    if await ch.reject_own_item_rent(callback, item, user.id):
        return # Нельзя арендовать свою вещь

    if await ch.ensure_rent_item_available_or_notify(callback, rental_service, item.id):
        return # вещь недоступна

    draft = RentalCreateDraft(
        item_id=item.id,
        renter_id=user.id,
        owner_id=item.user_id,
        deposit_amount=item.deposit
    )

    await state.clear()  # ✅ новый rent-flow
    await state.update_data(
        #item_id=item.id,
        rent_draft=draft.model_dump(mode="json"),
        rent_ui_message_id=None,
    )

    # ✅ отправляем ОТДЕЛЬНОЕ сообщение - “экран аренды” (не трогаем карточку объявления), чтобы дальше редактировать только его
    sent = await callback.message.answer(
        ch.format_start_date_rent_text(item),
        reply_markup=ch.build_start_date_keyboard(item.id),
        parse_mode="HTML"
    )

    await state.update_data(rent_ui_message_id=sent.message_id)
    await state.set_state(RentStates.start_date)


@rental_router.callback_query(RentStates.start_date, F.data.startswith(START_DATE_CB))
async def process_start_date(callback: CallbackQuery, state: FSMContext, item_service: ItemService, rental_service: RentalService) -> None:
    """Обработка выбранной даты начала аренды и переход к выбору даты окончания."""
    await callback.answer()

    parsed_start = await ch.parse_and_valid_start_date_str(callback, state)
    if parsed_start is None:
        return
    start_str, start_date = parsed_start

    # вызываем draft и сохраняем start_str в него
    stored_start = await ch.store_rent_start_date_or_abort(
        callback, state,  start_str, ch.rental_data_err, ch.not_item_for_rental
    )
    if stored_start is None:
        return
    item_id, rent_ui_message_id = stored_start

    item = await ch.load_item(callback, state, item_service.get_item_by_id, item_id,
                                            invalid_id_text=ch.not_item_for_rental, load_error_text=ch.serv_item_err,
                                            not_found_text=ch.not_item, rent_ui_message_id=rent_ui_message_id)
    if item is None:
        return

    if await ch.ensure_rent_item_available_or_notify(callback, rental_service, item.id):
        return # вещь недоступна

    await render_rent_ui(callback, state,
        ch.format_end_date_rent_text(item, start_str),
        build_rent_end_date_keyboard(
            start_date=start_date,
            min_days=item.min_rental_period or 1,
            max_days=item.max_rental_period or 30
        ),
        rent_ui_message_id
    )

    await state.set_state(RentStates.end_date)


@rental_router.callback_query(RentStates.end_date, F.data.startswith(END_DATE_CB))
async def process_end_date(callback: CallbackQuery, state: FSMContext, item_service: ItemService, rental_service: RentalService) -> None:
    """Обработка выбранной даты окончания аренды и показ подтверждения."""
    await callback.answer()

    parsed_end = await ch.parse_and_validate_end_date(callback, state)
    if parsed_end is None:
        return
    end_str, end_date, days = parsed_end

    # Достаём данные из FSM (вызываем draft и валидация)
    rent_ctx = await ch.get_rent_end_date_context_or_abort(callback, state, ch.no_rent_data_err)
    if rent_ctx is None:
        return
    draft, rent_ui_message_id, start_date_str = rent_ctx

    item = await ch.load_item(callback, state, item_service.get_item_by_id, draft.item_id,
                                            invalid_id_text=ch.not_item_for_rental, load_error_text=ch.serv_item_err,
                                            not_found_text=ch.not_item, rent_ui_message_id=rent_ui_message_id)
    if item is None:
        return

    if await ch.ensure_rent_item_available_or_notify(callback, rental_service, item.id):
        return # вещь недоступна

    days = await ch.validate_rent_period_or_notify(
        callback, state, start_date_str, end_date, days, item, rent_ui_message_id
    )
    if days is None:
        return

    # Запись в draft: дата окончания, цена, депозит-залог
    price_per_day, total_price = await ch.store_rent_end_date_and_amounts(
        state, draft, end_str, item, days,
    )

    # Кнопки подтверждения аренды
    keyboard = build_rent_confirmation_keyboard(start_date_str)
    # Текст подтверждения
    deposit = item.deposit if isinstance(item.deposit, Decimal) else Decimal(str(item.deposit or 0))
    total_with_deposit = (total_price + deposit).quantize(Decimal("0.01"))
    text = ch.format_rent_confirmation_text(item, start_date_str, end_str, days, price_per_day, total_price, deposit,
                                         total_with_deposit)
    await render_rent_ui(callback, state, text, keyboard, rent_ui_message_id)

    await state.set_state(RentStates.confirmation)


@rental_router.callback_query(RentStates.confirmation, F.data == CONFIRM_RENT_CB)
async def confirm_rent( callback: CallbackQuery, state: FSMContext, rental_service: RentalService, user_service: UserService,
                        item_service: ItemService, notification_service: NotificationService, user) -> None:
    """Создаёт сделку со статусом REQUESTED и уведомляет владельца."""
    await callback.answer()

    confirm_ctx = await ch.get_rent_confirm_context_or_abort(callback, state, ch.rental_data_err, ch.not_all_rental_data_err)
    if confirm_ctx is None:
        return
    draft, rent_ui_message_id = confirm_ctx

    item = await ch.load_item(callback, state, item_service.get_item_by_id, draft.item_id,
                                            invalid_id_text=ch.not_item_for_rental, load_error_text=ch.serv_item_err,
                                            not_found_text=ch.not_item, rent_ui_message_id=rent_ui_message_id)
    if item is None:
        return

    # if await ch.reject_own_item_rent(callback, item, user.id):
    #     return # Нельзя арендовать свою вещь

    if await ch.ensure_rent_item_available_or_notify(callback, rental_service, draft.item_id):
        return # вещь занята

    # Конвертация строк draft в строгие aware datetime
    parsed_dates = await ch.validate_rent_dates(callback, state,
        start_date_str=draft.start_date,
        end_date_str=draft.end_date,
        rent_ui_message_id=rent_ui_message_id,
    )
    if parsed_dates is None:
        return
    start_dt, end_dt, days_count = parsed_dates

    try:
        payload = RentalCreate(
            item_id=draft.item_id,
            renter_id=user.id, # берём из контекста (middleware), не доверяем state на 100%
            owner_id=draft.owner_id,
            start_date=start_dt,
            end_date=end_dt,
            total_price=draft.total_price,
            deposit_amount=draft.deposit_amount,
            #status=RentalStatus.REQUESTED,  # Начальный статус
        )
    except ValidationError:
        # Fatal: данные не проходят строгую схему → завершаем flow
        await abort_rent_flow(callback, state, ch.rental_data_err, rent_ui_message_id=rent_ui_message_id)
        return

    # Создаём сделку
    try:
        new_rental = await rental_service.create(payload)
    except ServiceError:
        # Recoverable: сервис не создал (например, конфликт/БД) → остаёмся в confirmation
        await send_or_edit(callback, "❌ Не удалось создать запрос аренды. Попробуйте позже.")
        return

    logger.info(f"[Rent] Создана аренда #{new_rental.id}")

    # -------------- Notification logic - уведомление владельцу товара о новом запросе -------------------
    # лучше еще подумать над этим:
    await ch.notify_item_owner_about_rent_request(user_service, notification_service, item, user, new_rental.id)
    # await message.answer("✅ Заявка на аренду отправлена владельцу.")
    # ---------------------------------------------------------------------------------------------------

    # Отображаем сообщение об успешном создании запроса
    text = ch.build_success_text(item, draft.start_date, draft.end_date, days_count, draft.total_price, draft.deposit_amount)
    await render_rent_ui(callback, state, text, ch.build_rent_success_keyboard(), rent_ui_message_id)

    await state.clear()


@rental_router.callback_query(F.data == CANCEL_RENT_FLOW_CB)
async def cancel_rent_flow(callback: CallbackQuery, state: FSMContext) -> None:
    """Fatal: пользователь отменил аренду → чистим FSM и обновляем rent-UI"""
    await callback.answer()

    data = await state.get_data()
    rent_ui_message_id = data.get("rent_ui_message_id")
    draft_dict = data.get("rent_draft") or {}
    item_id = draft_dict.get("item_id")

    await render_rent_ui(callback, state, ch.cancel_rent, ch.build_rent_cancel_keyboard(item_id), rent_ui_message_id)

    await state.clear()


@rental_router.callback_query(F.data == IGNORE_CB)
async def ignore_callback(callback: CallbackQuery) -> None:
    """No-op обработчик для служебных кнопок-заголовков."""
    await callback.answer()

# ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
"""
Recoverable ошибка → просто показываем сообщение и не чистим FSM (пользователь может попробовать снова).

Fatal ошибка (битый callback, item не найден/недоступен/сломанные данные) → завершаем rent-flow через 
единый helper: обновить rent-UI (если он уже есть) / иначе ответить обычным сообщением + state.clear().

    Recoverable:
      - ServiceError при чтении деталей → показываем сообщение, не ломаем ничего.
    Fatal:
      - битый rental_id в callback → показываем ошибку + кнопка назад
      - сделка не найдена/нет доступа → показываем “не найдено” + кнопка назад
"""
# ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────