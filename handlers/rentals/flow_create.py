import logging
from aiogram import F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton # Message,
from aiogram.fsm.context import FSMContext
from datetime import datetime, timezone, timedelta, time
from decimal import Decimal

from .router import rental_router

from services.item_service import ItemService
from services.user_service import UserService
from services.rental_service import RentalService
from services.notif_service import NotificationService

from states.rental import RentStates
from utils.functions import send_or_edit, render_rent_ui, abort_rent_flow
from utils.domain_exceptions import ItemNotAvailable
from utils.errors import ServiceError, ValidationError
from schemas.rental import RentalCreate, RentalCreateDraft
from keyboards.rental_kb import get_open_rental_keyboard, build_rent_end_date_keyboard, build_rent_confirmation_keyboard
from utils.notification import format_new_rental_request

logger = logging.getLogger(__name__)


IGNORE_CB = "ignore"

ITEM_DETAILS = "item_details:"
RENT_ITEM_CB = "rent_item:"
START_DATE_CB = "start_date:"
END_DATE_CB = "end_date:"
CONFIRM_RENT_CB = "confirm_rent"

BACK_TO_MENU_CB = "back_to_main_menu" # "back_to_menu" # "menu:main"
MY_RENTALS_CB = "rental_list" # back_to_rentals
CANCEL_RENT_FLOW_CB = "cancel_rent_flow" # new

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

def _format_item_not_available_message(exc: ItemNotAvailable) -> str:
    end_str = exc.end_date if exc.end_date else ""
    status = exc.status or "—"
    rental_id = exc.rental_id or "—"
    if end_str:
        return f"⛔ Эта вещь уже в аренде до {end_str}. Сделка #{rental_id} статус {status}."
    return f"⛔ Эта вещь уже в аренде. Сделка #{rental_id} статус {status}."

@rental_router.callback_query(F.data.startswith(RENT_ITEM_CB))
#@rental_router.callback_query(F.data.startswith("back_to_start_date:"))
async def start_rent_process(callback: CallbackQuery, state: FSMContext, item_service: ItemService, rental_service: RentalService, user) -> None:
    """Старт процесса аренды"""

    await callback.answer()

    try:
        item_id = int(callback.data.split(":", 1)[1])
        logger.info(f"Пользователь {user.id} начинает процесс аренды для товара {item_id}")
    except (IndexError, ValueError):
        # Fatal: некорректная кнопка → чистим FSM и выходим
        await abort_rent_flow(callback, state, "⚠️ Не удалось распознать объявление.")
        return

    # Получаем товар
    try:
        item = await item_service.get_item_by_id(item_id)
    except ServiceError:
        # Recoverable: сервис/БД временно недоступны, FSM не трогаем
        await send_or_edit(callback, "⚠️ Не удалось загрузить объявление. Попробуйте позже.")
        return

    if not item:
        # Fatal: объявления нет → чистим FSM
        await abort_rent_flow(callback, state, "❌ Объявление не найдено.")
        return

    # Нельзя арендовать свою вещь
    if item.user_id == user.id:
        # Recoverable: пользователь просто ошибся, FSM не чистим
        await send_or_edit(callback, "Вы не можете арендовать свою собственную вещь.")
        return

    # Проверь, выполняет ли она свою функцию!
    # доменная проверка доступности (защита от старых кнопок/гонок) (ДО запуска выбора дат)
    # тут не должен быть пользователь (кнопки нет), но это защита от: старых сообщений, параллельных кликов, гонок.
    try:
        await rental_service.ensure_item_available(item.id)
    except ItemNotAvailable as e:
        # Recoverable: вещь занята, просто показываем сообщение
        await callback.message.answer(_format_item_not_available_message(e))
        return

    draft = RentalCreateDraft(
        item_id=item.id,
        renter_id=user.id,
        owner_id=item.user_id,
        deposit_amount=item.deposit
    )

    await state.clear()  # ✅ новый rent-flow — чистим старый мусор
    await state.update_data(
        #item_id=item.id,
        rent_draft=draft.model_dump(mode="json"),
        rent_ui_message_id=None,
    )

    keyboard = _build_start_date_keyboard(item.id)
    text = _format_start_date_rent_text(item)

    # ✅ отправляем ОТДЕЛЬНОЕ сообщение - “экран аренды” (не трогаем карточку объявления),
    # чтобы дальше редактировать только его
    sent = await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")

    await state.update_data(rent_ui_message_id=sent.message_id)

    await state.set_state(RentStates.start_date)


@rental_router.callback_query(RentStates.start_date, F.data.startswith(START_DATE_CB))
async def process_start_date(callback: CallbackQuery, state: FSMContext, item_service: ItemService, rental_service: RentalService) -> None:
    """Обработка выбранной даты начала аренды и переход к выбору даты окончания."""

    await callback.answer()

    try:
        start_str = callback.data.split(":", 1)[1]  # dd.mm.YYYY (12.03.2025)
        start_date = datetime.strptime(start_str, "%d.%m.%Y").date() # date(2025, 3, 12)
    except (IndexError, ValueError):
        # Fatal: битый callback-data → завершаем flow
        await abort_rent_flow(callback, state,"⚠️ Некорректная дата начала. Попробуйте начать аренду заново.")
        return

    # защита от tampered callback: нельзя выбрать дату начала в прошлом или сегодня
    today = datetime.now(timezone.utc).date()
    if start_date <= today:
        await send_or_edit(callback, "❌ Дата начала должна быть не раньше завтрашнего дня.")
        return

    data = await state.get_data()
    rent_ui_message_id = data.get("rent_ui_message_id")
    rent_draft_dict = data.get("rent_draft") or {}

    try:
        draft = RentalCreateDraft.model_validate(rent_draft_dict)
    except ValidationError:
        # Fatal: draft повреждён → завершаем flow
        await abort_rent_flow(
            callback,
            state,
            "❌ Данные аренды повреждены. Начните заново.",
            rent_ui_message_id=rent_ui_message_id
        )
        return

    if not draft.item_id:
        # Fatal: нет item_id → завершаем flow
        await abort_rent_flow(
            callback,
            state,
            "❌ Не удалось определить объявление для аренды. Начните заново.",
            rent_ui_message_id=rent_ui_message_id
        )
        return

    item_id = draft.item_id
    try:
        item = await item_service.get_item_by_id(item_id)
    except ServiceError:
        # Recoverable: временная ошибка сервиса/БД → остаёмся в этом шаге
        await send_or_edit(callback, "⚠️ Не удалось загрузить объявление. Попробуйте позже.")
        return

    if not item:
        # Fatal: item удалён/не найден → завершаем flow
        await abort_rent_flow(
            callback, state,
            "❌ Объявление не найдено. Возможно, оно удалено.",
            rent_ui_message_id=rent_ui_message_id
        )
        return

    # Доменная проверка доступности (страховка от гонок)
    try:
        await rental_service.ensure_item_available(item_id)
    except ItemNotAvailable as e:
        # Recoverable: вещь занята, просто показываем сообщение
        await callback.message.answer(_format_item_not_available_message(e))
        return

    draft.start_date = start_str
    await state.update_data(rent_draft=draft.model_dump(mode="json"))

    # Готовим диапазон дат
    min_days = item.min_rental_period or 1
    max_days = item.max_rental_period or 30

    keyboard = build_rent_end_date_keyboard(start_date=start_date, min_days=min_days, max_days=max_days)
    text = _format_end_date_rent_text(item, start_str)

    await render_rent_ui(callback, state, text, keyboard, rent_ui_message_id)

    # Переходим к выбору даты окончания
    await state.set_state(RentStates.end_date)


@rental_router.callback_query(RentStates.end_date, F.data.startswith(END_DATE_CB))
async def process_end_date(callback: CallbackQuery, state: FSMContext, item_service: ItemService, rental_service: RentalService) -> None:
    """Обработка выбранной даты окончания аренды и показ подтверждения."""

    await callback.answer()

    try:
        payload = callback.data.split(":", 2) # "end_date:DD.MM.YYYY:<days>" (:12.03.2025:3)
        end_str = payload[1] # "15.03.2025"
        days = int(payload[2]) # 3
        end_date = datetime.strptime(end_str, "%d.%m.%Y").date()
    except (IndexError, ValueError):
        # Fatal: битый callback-data → завершаем flow
        await abort_rent_flow(callback, state, "❌ Некорректная дата окончания.")
        return

    if days < 1:
        # Fatal: некорректная длительность (кнопка битая) → завершаем flow
        await abort_rent_flow(callback, state, "❌ Некорректная длительность аренды.")
        return

    # 2️⃣ Достаём данные из FSM
    data = await state.get_data()
    rent_ui_message_id = data.get("rent_ui_message_id")
    draft_dict = data.get("rent_draft") or {}

    try:
        draft = RentalCreateDraft.model_validate(draft_dict)
    except ValidationError:
        # Fatal: draft повреждён → завершаем flow
        await abort_rent_flow(
            callback,
            state,
            "❌ Данные аренды повреждены. Начните заново.",
            rent_ui_message_id=rent_ui_message_id
        )
        return

    item_id = draft.item_id
    start_date_str = draft.start_date
    if not item_id or not start_date_str:
        # Fatal: нет item_id/start_date → завершаем flow
        await abort_rent_flow(
            callback,
            state,
            "❌ Не удалось восстановить данные аренды. Начните заново.",
            rent_ui_message_id=rent_ui_message_id
        )
        return

    try:
        item = await item_service.get_item_by_id(item_id)
    except ServiceError:
        # Recoverable: временная ошибка сервиса/БД → остаёмся на этом шаге
        await send_or_edit(callback, "⚠️ Не удалось загрузить объявление. Попробуйте позже.")
        return

    if not item:
        # Fatal: item удалён/не найден → завершаем flow
        await abort_rent_flow(
            callback,
            state,
            "❌ Объявление не найдено. Возможно, оно удалено.",
            rent_ui_message_id=rent_ui_message_id
        )
        return

    # Доменная проверка доступности (страховка от гонок)
    try:
        await rental_service.ensure_item_available(item.id)
    except ItemNotAvailable as e:
        # Recoverable: вещь занята → просто сообщаем
        await callback.message.answer(_format_item_not_available_message(e))
        return

    try:
        start_date = datetime.strptime(draft.start_date, "%d.%m.%Y").date()
    except ValueError:
        # Fatal: start_date битая → завершаем flow
        await abort_rent_flow(
            callback,
            state,
            "❌ Некорректная дата начала. Начните заново.",
            rent_ui_message_id=rent_ui_message_id
        )
        return

    if end_date <= start_date:
        # Recoverable: пользователь выбрал “не туда” → остаёмся в шаге end_date (без clear)
        await send_or_edit(callback, "❌ Дата окончания должна быть позже даты начала.")
        return

    # (опционально) проверим длительность по датам
    actual_days = (end_date - start_date).days
    if actual_days != days:
        # Recoverable: не фейлим, а синхронизируем на фактическое значение
        days = actual_days

    min_days = item.min_rental_period or 1
    max_days = item.max_rental_period or 30

    if days < min_days:
        # Recoverable: коротко → остаёмся на выборе end_date
        await send_or_edit(callback, f"❌ Минимальный срок аренды: {min_days} дн.")
        return

    if days > max_days:
        # Recoverable: длинно → остаёмся на выборе end_date
        await send_or_edit(callback, f"❌ Максимальный срок аренды: {max_days} дн.")
        return

    # Считаем итоговую стоимость
    # item.price может быть Decimal — ок. Если вдруг float/int — приведём к Decimal.
    price_per_day = item.price if isinstance(item.price, Decimal) else Decimal(str(item.price))
    total_price = (price_per_day * Decimal(days)).quantize(Decimal("0.01"))

    # Обновляем draft
    draft.end_date = end_str
    draft.total_price = total_price
    # deposit_amount уже может быть проставлен на старте из item.deposit
    if draft.deposit_amount is None and getattr(item, "deposit", None) is not None:
        draft.deposit_amount = item.deposit

    await state.update_data(rent_draft=draft.model_dump(mode="json"))

    # Кнопки подтверждения аренды
    keyboard = build_rent_confirmation_keyboard(start_date_str)

    deposit = item.deposit if isinstance(item.deposit, Decimal) else Decimal(str(item.deposit or 0))
    total_with_deposit = (total_price + deposit).quantize(Decimal("0.01"))

    # Текст подтверждения
    text = _format_rent_confirmation_text(item, start_date_str, end_str, days, price_per_day, total_price, deposit, total_with_deposit)

    await render_rent_ui(callback, state, text, keyboard, rent_ui_message_id)

    # Переходим в состояние подтверждения аренды
    await state.set_state(RentStates.confirmation)

@rental_router.callback_query(RentStates.confirmation, F.data == CONFIRM_RENT_CB)
async def confirm_rent(
    callback: CallbackQuery,
    state: FSMContext,
    rental_service: RentalService,
    user_service: UserService,
    item_service: ItemService,
    notification_service: NotificationService,
    user
) -> None:
    """Создаёт сделку со статусом REQUESTED и уведомляет владельца."""

    await callback.answer()
    # chat_id = callback.message.chat.id

    data = await state.get_data()
    rent_ui_message_id = data.get("rent_ui_message_id")
    draft_dict = data.get("rent_draft") or {}

    try:
        draft = RentalCreateDraft.model_validate(draft_dict)
    except ValidationError:
        # Fatal: draft повреждён → завершаем flow
        await abort_rent_flow(
            callback,
            state,
            "❌ Данные аренды повреждены. Начните заново.",
            rent_ui_message_id=rent_ui_message_id
        )
        return

    item_id = draft.item_id
    start_date_str = draft.start_date
    end_date_str = draft.end_date
    owner_id = draft.owner_id
    renter_id = draft.renter_id

    if not (item_id and owner_id and renter_id and start_date_str and end_date_str):
        # Fatal: не хватает данных → завершаем flow
        await abort_rent_flow(
            callback,
            state,
            "❌ Не хватает данных для создания аренды. Начните заново.",

        )
        return

    try:
        item = await item_service.get_item_by_id(item_id)
    except ServiceError:
        # Recoverable: временная ошибка сервиса/БД → остаёмся в confirmation
        await send_or_edit(callback, "⚠️ Не удалось загрузить объявление. Попробуйте позже.")
        return

    if not item:
        # Fatal: item удалён → завершаем flow
        await abort_rent_flow(
            callback,
            state,
            "❌ Объявление не найдено. Возможно, оно удалено.",
            rent_ui_message_id=rent_ui_message_id
        )
        return

    # # нельзя арендовать своё (ну для супер безопасности)
    # Recoverable: пользователь пытается арендовать своё
    # if item.user_id == user.id:
    #     await callback.answer("Вы не можете арендовать свою собственную вещь.", show_alert=True)
    #     return

    # Доменная проверка доступности (страховка от гонок)
    try:
        await rental_service.ensure_item_available(item_id)
    except ItemNotAvailable as e:
        # Recoverable: вещь занята → просто сообщаем
        await callback.message.answer(_format_item_not_available_message(e))
        return

    try:
        start_date = datetime.strptime(start_date_str, "%d.%m.%Y").date()
        end_date = datetime.strptime(end_date_str, "%d.%m.%Y").date()
    except ValueError:
        # Fatal: даты битые → завершаем flow
        await abort_rent_flow(
            callback,
            state,
            "❌ Некорректные даты. Начните заново.",
            rent_ui_message_id=rent_ui_message_id
        )
        return

    if end_date <= start_date:
        # Recoverable: логическая ошибка → остаёмся в confirmation
        await send_or_edit(callback, "❌ Дата окончания должна быть позже даты начала.")
        return

    tz = datetime.now(timezone.utc).astimezone().tzinfo
    start_dt = datetime.combine(start_date, time.min).replace(tzinfo=tz)
    end_dt = datetime.combine(end_date, time.min).replace(tzinfo=tz)

    total_price = draft.total_price
    deposit_amount = draft.deposit_amount

    try:
        payload = RentalCreate(
            item_id=item_id,
            renter_id=user.id, # берём из контекста (middleware), не доверяем state на 100%
            owner_id=owner_id,
            start_date=start_dt,
            end_date=end_dt,
            total_price=total_price,
            deposit_amount=deposit_amount,
            #status=RentalStatus.REQUESTED,  # Начальный статус
        )
    except ValidationError:
        # Fatal: данные не проходят строгую схему → завершаем flow
        await abort_rent_flow(
            callback,
            state,
            "❌ Ошибка в данных аренды. Начните заново.",
            rent_ui_message_id=rent_ui_message_id
        )
        return

    # Создаём сделку через сервис
    try:
        new_rental = await rental_service.create(payload)
    except ServiceError:
        # Recoverable: сервис не создал (например, конфликт/БД) → остаёмся в confirmation
        await send_or_edit(callback, "❌ Не удалось создать запрос аренды. Попробуйте позже.")
        return

    logger.info(f"[Rent] Создана аренда #{new_rental.id}")

    # лучше еще подумать над этим:
    # -------------- Notification logic - уведомление владельцу товара о новом запросе -------------------
    try:
        owner = await user_service.get_by_id(item.user_id)
    except ServiceError:
        owner = None

    owner_tg_id = getattr(owner, "telegram_id", None) if owner else None

    notify_text = format_new_rental_request(
        item_title=getattr(item, "title", "—"),
        renter_username=getattr(user, "username", None),
    )

    if owner_tg_id:
        # ✅ notify_user сам ловит TelegramBadRequest/Exception и логирует
        await notification_service.notify_user(
            owner_tg_id,
            notify_text,
            reply_markup=get_open_rental_keyboard(new_rental.id),
        )
    else:
        logger.warning(
            "Не удалось отправить уведомление владельцу user_id=%s: отсутствует telegram_id или владелец не найден",
            item.user_id, # owner_id
        )
    #await message.answer("✅ Заявка на аренду отправлена владельцу.")
    # ---------------------------------------------------------------------------------------------------

    days_count = (end_date - start_date).days
    # 3️⃣ Отображаем сообщение об успешном создании запроса
    text = _build_success_text(item, start_date_str, end_date_str, days_count, total_price, deposit_amount)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📋 Мои сделки", callback_data=MY_RENTALS_CB)],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data=BACK_TO_MENU_CB)],
        ]
    )

    await render_rent_ui(callback, state, text, keyboard, rent_ui_message_id)

    await state.clear()

# не обдумывал, пусть пока так
@rental_router.callback_query(F.data == CANCEL_RENT_FLOW_CB)
async def cancel_rent_flow(callback: CallbackQuery, state: FSMContext) -> None:
    """Fatal (user intent): пользователь отменил аренду → чистим FSM и обновляем rent-UI."""

    await callback.answer()

    data = await state.get_data()
    rent_ui_message_id = data.get("rent_ui_message_id")
    draft_dict = data.get("rent_draft") or {}
    item_id = draft_dict.get("item_id")  # draft у тебя хранится как dict

    text = "❌ <b>Аренда отменена.</b>\n\nВы можете вернуться к объявлению или в меню."

    rows: list[list[InlineKeyboardButton]] = []
    if item_id:
        rows.append([InlineKeyboardButton(text="🔙 К объявлению", callback_data=f"{ITEM_DETAILS}{item_id}")])
    rows.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data=BACK_TO_MENU_CB)])
    markup = InlineKeyboardMarkup(inline_keyboard=rows)

    # обновляем rent-ui, если он есть, иначе просто отвечаем сообщением
    await render_rent_ui(callback, state, text, markup, rent_ui_message_id)

    await state.clear()


@rental_router.callback_query(F.data == IGNORE_CB)
async def ignore_callback(callback: CallbackQuery) -> None:
    """No-op обработчик для служебных кнопок-заголовков."""
    await callback.answer()


# -----------------------------------------------------------------------


START_DATE_DAYS_AHEAD = 5
def _build_start_date_keyboard(item_id: int, days_ahead: int = START_DATE_DAYS_AHEAD) -> InlineKeyboardMarkup:
    """Собирает клавиатуру выбора даты начала аренды."""

    # Формируем кнопки выбора даты начала
    today = datetime.now(timezone.utc)
    rows = [[InlineKeyboardButton(text="📅 Выберите дату начала аренды:", callback_data=IGNORE_CB)]] # dummy_start

    for i in range(1, days_ahead + 1):
        date = today + timedelta(days=i)
        ds = date.strftime("%d.%m.%Y") # для кнопок
        rows.append([InlineKeyboardButton(text=ds, callback_data=f"{START_DATE_CB}{ds}")])

    rows.append([
        InlineKeyboardButton(text="🔙 Назад к объявлению", callback_data=f"{ITEM_DETAILS}{item_id}")
    ]) # убираем?

    return InlineKeyboardMarkup(inline_keyboard=rows)

def _format_start_date_rent_text(item) -> str:
    """Формирует текст первого экрана аренды."""
    return (
        f"🤝 <b>Аренда вещи</b>\n\n"
        f"Вы собираетесь арендовать: <b>{item.title}</b>\n"
        f"💰 Цена: <b>{item.price} ₽/день</b>\n"
        f"🔒 Залог: <b>{item.deposit or 'Нет'} ₽</b>\n\n"
        "Выберите дату начала аренды:"
    )

def _format_end_date_rent_text(item, start_str: str) -> str:
    """Формирует текст шага выбора даты окончания."""
    return (
        f"🤝 <b>Аренда вещи</b>\n\n"
        f"Вы собираетесь арендовать товар: <b>{item.title}</b>\n"
        f"📅 Дата начала аренды: <b>{start_str}</b>\n"
        f"💰 Цена: <b>{item.price} ₽/день</b>\n"
        f"🔒 Залог: <b>{item.deposit or 'Нет'} ₽</b>\n\n"
        "Теперь выберите дату окончания аренды:"
    )

def _format_rent_confirmation_text(
    item,
    start_date_str: str,
    end_date_str: str,
    days: int,
    price_per_day: Decimal,
    total_price: Decimal,
    deposit: Decimal,
    total_with_deposit: Decimal,
) -> str:
    """Текст экрана подтверждения аренды."""

    return (
        f"🤝 <b>Подтверждение аренды</b>\n\n"
        f"📦 <b>{item.title}</b>\n"
        # f"👤 Владелец: {...}\n"
        f"📍 {item.location or '-'}\n\n"
        
        f"<b>Выбранный период:</b>\n"
        f"📅 Начало: <b>{start_date_str}</b>\n"
        f"📅 Окончание: <b>{end_date_str}</b>\n"
        f"⏱️ Длительность: <b>{days} дн.</b>\n\n"
        
        f"<b>Расчёт стоимости:</b>\n"
        f"💰 {price_per_day} ₽/день × {days} дн. = <b>{total_price} ₽</b>\n"
        f"🛡 Залог: <b>{deposit if deposit > 0 else 'Нет'} ₽</b>\n"
        f"💵 Итого к оплате (после подтверждения владельцем): <b>{total_with_deposit} ₽</b>\n\n"
        
        "❗ Залог будет возвращен после завершения аренды и возврата вещи в исходном состоянии.\n\n"
        "Отправить запрос на аренду владельцу?"
    )

def _build_success_text(
        item,
        start_date: str,
        end_date: str,
        days: int,
        total_price: Decimal,
        deposit: Decimal,
) -> str:
    """Текст экрана успеха для аренды."""
    return (
        f"✅ <b>Запрос на аренду отправлен!</b>\n\n"
        f"📦 <b>{item.title}</b>\n"
        f"📅 {start_date} — {end_date}\n"
        f"⏱️ {days} дн.\n\n"
        f"💰 Стоимость: <b>{total_price} ₽</b>\n"
        f"💵🛡 Залог: <b>{deposit if deposit is not None else 'Нет'} ₽</b>\n\n"
        f"ℹ️ Статус: <b>Ожидает подтверждения владельцем</b>\n\n"
        f"Вы получите уведомление, когда владелец ответит на ваш запрос."
    )
