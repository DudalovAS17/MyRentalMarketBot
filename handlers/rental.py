import logging
from aiogram import F, Router
from aiogram.types import (CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton,
                           ReplyKeyboardMarkup, KeyboardButton)
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta
from aiogram.exceptions import TelegramBadRequest
from utils.functions import send_or_edit


from states.rental import RentStates
from schemas.rental import RentalCreate
from db.models.rental import RentalStatus

from handlers.rental_ui import build_rental_details_ui

from states.review import ReviewStates

from services.item_service import ItemService
from services.user_service import UserService
from services.rental_service import RentalService
from services.review_service import ReviewService

from utils.domain_exceptions import ItemNotAvailable
from keyboards.user_kb import get_review_rating_keyboard

logger = logging.getLogger(__name__)
rental_router = Router(name="items")

# Константы для callback_data
RENTAL_CB = "rental"
RETURN_CB = "return"
CONFIRM_CB = "confirm"
REVIEW_CB = "review"
DISPUTE_CB = "dispute"
CANCEL_CB = "cancel"
BACK_CB = "back"


def _format_item_not_available_message(exc: ItemNotAvailable) -> str:
    end_str = exc.end_date if exc.end_date else "" #exc.end_date.strftime("%d.%m.%Y") if exc.end_date else None
    # end_str = exc.end_date or None
    status = exc.status or "—"
    rental_id = exc.rental_id or "—"
    if end_str:
        return f"⛔ Эта вещь уже в аренде до {end_str}. Сделка #{rental_id} статус {status}."
    return f"⛔ Эта вещь уже в аренде. Сделка #{rental_id} статус {status}."

@rental_router.callback_query(F.data.startswith("rent_item:")) # callback_data=f"rent:{item_id}" (хендлер категории)
#@rental_router.callback_query(F.data.startswith("back_to_start_date:")) # эта логика у нас также через "rent_item:"
async def start_rent_process(
    callback: CallbackQuery,
    state: FSMContext,
    item_service: ItemService,
    rental_service: RentalService,
    user,
):
    """Старт процесса аренды"""

    item_id = int(callback.data.split(":")[1])
    #user_id = callback.from_user.id
    await callback.answer()
    logger.info(f"Пользователь {user.id} начинает процесс аренды для товара {item_id}")

    # 1️⃣ Получаем товар
    item = await item_service.get_item_by_id(item_id)
    if not item:
        await callback.message.edit_text("❌ Объявление не найдено.",)
        logger.warning(f"Товар {item_id} не найден в БД.")
        return

    # 2️⃣ Нельзя арендовать свою вещь
    if item.user_id == user.id: # Проверяем, что пользователь не владелец
        await callback.answer(
            "Вы не можете арендовать свою собственную вещь.",
            show_alert=True
        )
        logger.warning(f"Владелец пытается арендовать свой товар.")
        return

    #!!!!!!!! стоп: доменная проверка ДО запуска выбора дат !!!!!!!!!!!!!!!
    # тут не должен быть пользователь (кнопки нет), но это защита от: старых сообщений, параллельных кликов, гонок.
    try:
        await rental_service.ensure_item_available(item.id)
    except ItemNotAvailable as e:
        # await callback.answer() # нет! ты отправляешь новое сообщение -> Telegram сам уберёт “часики” при answer()
        await callback.message.answer(_format_item_not_available_message(e))
        return
    # !!!!!!!!!!!!-

    # 3️⃣ Сохраняем данные в FSM
    await state.update_data(
        rent_item={
            "id": item.id,
            "name": item.title,
            "price_per_day": item.price,
            "deposit_amount": item.deposit,
            "owner_id": item.user_id,
            "min_rent_days": item.min_rental_period or 1,
            "max_rent_days": item.max_rental_period or 30,
            "location": item.location,
        }
    )

    # 4️⃣ Формируем кнопки выбора даты начала
    today = datetime.now()
    rows = [[InlineKeyboardButton(text="📅 Выберите дату начала аренды:", callback_data="ignore")]]  # dummy_start

    for i in range(1, 6):
        date = today + timedelta(days=i)
        ds = date.strftime("%d.%m.%Y")
        rows.append([InlineKeyboardButton(text=ds, callback_data=f"start_date:{ds}")])

    # Кнопка назад
    rows.append([
        InlineKeyboardButton(
            text="🔙 Назад к объявлению",
            callback_data=f"item_details:{item.id}"
        )
    ])

    keyboard = InlineKeyboardMarkup(inline_keyboard=rows)

    # 5️⃣ Формируем сообщение
    text = (
        f"🤝 <b>Аренда вещи</b>\n\n"
        f"Вы  собираетесь арендовать: <b>{item.title}</b>\n"
        f"💰 Цена: <b>{item.price} ₽/день</b>\n"
        f"🔒 Залог: <b>{item.deposit or 'Нет'} ₽</b>\n\n"
        f"Выберите дату начала аренды:"
    )

    #await callback.message.edit_text(
    #    text,
    #    reply_markup=keyboard,
    #    parse_mode="HTML"
    #)

    # ✅ отправляем ОТДЕЛЬНОЕ сообщение (не трогаем карточку)
    sent = await callback.message.answer(
        text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )

    # ✅ сохраняем message_id “экрана аренды”, чтобы дальше редактировать только его
    await state.update_data(rent_ui_message_id=sent.message_id)

    await state.set_state(RentStates.start_date)


@rental_router.callback_query(RentStates.start_date, F.data.startswith("start_date:"))
async def process_start_date(
    callback: CallbackQuery,
    state: FSMContext,
    user,
):
    """Обработка выбранной даты начала аренды и переход к выбору даты окончания."""

    await callback.answer()

    # 1️⃣ Получаем дату из callback_data
    _, date_str = callback.data.split(":")  # "start_date:12.03.2025" → берём вторую часть
    logger.info(f"[Rent] User {user.id} выбрал стартовую дату: {date_str}")

    # 2️⃣ Достаём данные из FSM
    data = await state.get_data()
    rent_item = data.get("rent_item")

    rent_ui_message_id = data.get("rent_ui_message_id") # логика - редактировать сообщение “экрана аренды”

    if not rent_item:
        logger.warning(f"[Rent] rent_item отсутствует в FSM для пользователя {user.id}")
        #await callback.message.edit_text("❌ Ошибка. Попробуйте начать аренду заново.")
        if rent_ui_message_id:
            await callback.bot.edit_message_text(
                chat_id=callback.message.chat.id,
                message_id=rent_ui_message_id,
                text="❌ Ошибка. Попробуйте начать аренду заново.",
                parse_mode="HTML",
            )
        else:
            sent = await callback.message.answer("❌ Ошибка. Попробуйте начать аренду заново.", parse_mode="HTML")
            await state.update_data(rent_ui_message_id=sent.message_id)

        return

    item_id = rent_item["id"]

    # Сохраняем дату начала
    await state.update_data(start_date=date_str)

    # 3️⃣ Готовим диапазон дат
    try:
        start_dt = datetime.strptime(date_str, "%d.%m.%Y")
    except ValueError:
        await callback.message.edit_text("❌ Ошибка формата даты. Попробуйте снова.")
        return

    min_days = rent_item["min_rent_days"]
    max_days = rent_item["max_rent_days"]

    # Показываем варианты до max_days, но не более ~10-14 для читаемости
    limit_days = min(max_days, 7)

    # 4️⃣ Строим клавиатуру выбора даты окончания
    rows = [
        [InlineKeyboardButton(text="📅 Выберите дату окончания аренды:", callback_data="ignore")]
    ]

    for days in range(min_days, limit_days + 1):
        end_dt = start_dt + timedelta(days=days)
        end_str = end_dt.strftime("%d.%m.%Y")

        rows.append([
            InlineKeyboardButton(
                text=f"{end_str} ({days} дн.)",
                callback_data=f"end_date:{end_str}:{days}"
            )
        ])

    # кнопка назад
    rows.append([
        InlineKeyboardButton(
            text="🔙 Назад к выбору даты начала",
            callback_data=f"rent_item:{item_id}"
        )
    ])

    keyboard = InlineKeyboardMarkup(inline_keyboard=rows)

    # 5️⃣ Формируем текст сообщения
    text = (
        f"🤝 <b>Аренда вещи</b>\n\n"
        f"Вы собираетесь арендовать товар: <b>{rent_item['name']}</b>\n"
        f"📅 Дата начала аренды: <b>{date_str}</b>\n"
        f"💰 Цена: <b>{rent_item['price_per_day']} ₽/день</b>\n"
        f"🔒 Залог: <b>{rent_item['deposit_amount'] or 'Нет'} ₽</b>\n\n"
        f"Теперь выберите дату окончания аренды:"
    )

    #await callback.message.edit_text(
    #    text,
    #    reply_markup=keyboard,
    #    parse_mode="HTML"
    #)

    if rent_ui_message_id:
        await callback.bot.edit_message_text(
            chat_id=callback.message.chat.id,
            message_id=rent_ui_message_id,
            text=text,
            reply_markup=keyboard,
            parse_mode="HTML",
        )
    else: # ???
        sent = await callback.message.answer(
            text,
            reply_markup=keyboard,
            parse_mode="HTML",
        )
        await state.update_data(rent_ui_message_id=sent.message_id)

    # остаёмся в том же состоянии FSM
    await state.set_state(RentStates.end_date)


@rental_router.callback_query(RentStates.end_date, F.data.startswith("end_date:"))
async def process_end_date(
    callback: CallbackQuery,
    state: FSMContext,
    user,
):
    """Обработка выбранной даты окончания аренды и показ подтверждения."""

    await callback.answer()

    # 1️⃣ Парсим данные из callback_data
    # end_date:12.03.2025:3
    _, end_date_str, days_str = callback.data.split(":")
    days_count = int(days_str)

    logger.info(f"[Rent] User {user.id} выбрал дату окончания {end_date_str} ({days_count} дн.)")

    # 2️⃣ Достаём данные из FSM
    data = await state.get_data()
    rent_item = data.get("rent_item")
    start_date = data.get("start_date")

    rent_ui_message_id = data.get("rent_ui_message_id")  # логика - редактировать сообщение “экрана аренды”

    if not rent_item or not start_date:
        logger.warning(f"[Rent] Нет rent_item/start_date в FSM у {user.id}")
        #await callback.message.edit_text("❌ Ошибка. Попробуйте начать аренду заново.")
        if rent_ui_message_id:
            await callback.bot.edit_message_text(
                chat_id=callback.message.chat.id,
                message_id=rent_ui_message_id,
                text="❌ Ошибка. Попробуйте начать аренду заново.",
                parse_mode="HTML",
            )
        else:
            sent = await callback.message.answer("❌ Ошибка. Попробуйте начать аренду заново.", parse_mode="HTML")
            await state.update_data(rent_ui_message_id=sent.message_id)

        return

    item_id = rent_item["id"]

    # 3️⃣ Обновляем FSM
    await state.update_data(
        end_date=end_date_str,
        days_count=days_count,
        total_price=rent_item["price_per_day"] * days_count
    )

    price_per_day = rent_item["price_per_day"]
    total_price = price_per_day * days_count
    deposit = rent_item["deposit_amount"] or 0

    # Сохраняем общую стоимость аренды
    # await state.update_data(rent_item={"total_price": total_price})

    # 4️⃣ Кнопки подтверждения аренды
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton( text="✅ Отправить запрос владельцу", callback_data="confirm_rent")],
            [InlineKeyboardButton(text="🔙 Изменить дату окончания", callback_data=f"start_date:{start_date}")],
            [InlineKeyboardButton(text="❌ Отменить аренду", callback_data=f"item_details:{item_id}")],
        ]
    )

    # 5️⃣ Текст подтверждения
    text = (
        f"🤝 <b>Подтверждение аренды</b>\n\n"
        f"📦 <b>{rent_item['name']}</b>\n"
        f"👤 Владелец: {rent_item.get('owner_name', '—')}\n" # ??? owner_id
        f"📍 {rent_item.get('location', '—')}\n\n"

        f"<b>Выбранный период:</b>\n"
        f"📅 Начало: <b>{start_date}</b>\n"
        f"📅 Окончание: <b>{end_date_str}</b>\n"
        f"⏱️ Длительность: <b>{days_count} дн.</b>\n\n"

        f"<b>Расчёт стоимости:</b>\n"
        f"💰 {price_per_day} ₽/день × {days_count} дн. = <b>{total_price} ₽</b>\n"
        f"🛡 Залог: <b>{deposit or 'Нет'} ₽</b>\n"
        f"💵 Итого к оплате (после подтверждения владельцем): <b>{total_price + deposit} ₽</b>\n\n"

        f"❗ Залог будет возвращен после завершения аренды и возврата вещи в исходном состоянии.\n\n"
        f"Отправить запрос на аренду владельцу?"
    )

    #await callback.message.edit_text(
    #    text,
    #    reply_markup=keyboard,
    #    parse_mode="HTML"
    #)

    if rent_ui_message_id:
        await callback.bot.edit_message_text(
            chat_id=callback.message.chat.id,
            message_id=rent_ui_message_id,
            text=text,
            reply_markup=keyboard,
            parse_mode="HTML",
        )
    else: # ???
        sent = await callback.message.answer(
            text,
            reply_markup=keyboard,
            parse_mode="HTML",
        )
        await state.update_data(rent_ui_message_id=sent.message_id)


    # 6️⃣ Переходим в состояние подтверждения аренды
    await state.set_state(RentStates.confirmation)


@rental_router.callback_query(RentStates.confirmation, F.data == "confirm_rent")
async def confirm_rent(
    callback: CallbackQuery,
    state: FSMContext,
    rental_service: RentalService,
    #user_service: UserService,
    #item_service: ItemService,
    user
):
    """Создаёт сделку со статусом REQUESTED и уведомляет владельца."""

    await callback.answer()
    data = await state.get_data()

    # Получаем данные аренды из контекста
    rent_item = data.get("rent_item")
    start_date = data.get("start_date")
    end_date = data.get("end_date")
    days_count = data.get("days_count")
    total_price = data.get("total_price")

    rent_ui_message_id = data.get("rent_ui_message_id")
    chat_id = callback.message.chat.id

    if not rent_item or not start_date or not end_date:
        #await callback.message.edit_text("❌ Ошибка: данные аренды не найдены. Попробуйте начать заново.")
        err_text = "❌ Ошибка: данные аренды не найдены. Попробуйте начать заново."

        if rent_ui_message_id:
            await callback.bot.edit_message_text(
                chat_id=chat_id,
                message_id=rent_ui_message_id,
                text=err_text,
                parse_mode="HTML",
            )
        else:
            await callback.message.answer(err_text, parse_mode="HTML")

        await state.clear() # Очищаем некорректные данные
        return

    logger.info(f"[Rent] User {user.id} подтверждает аренду товара {rent_item['id']}")

    # 1️⃣ Преобразуем даты из строк в datetime объекты
    try:
        start_dt = datetime.strptime(start_date, "%d.%m.%Y") # (f"{start_date} 00:00:00", "%d.%m.%Y %H:%M:%S")
        end_dt = datetime.strptime(end_date, "%d.%m.%Y") # (f"{end_date]} 23:59:59", "%d.%m.%Y %H:%M:%S")
    except ValueError:
        #await callback.message.edit_text("❌ Ошибка формата дат. Выберите даты заново.")
        err_text = "❌ Ошибка формата дат. Выберите даты заново."

        if rent_ui_message_id:
            await callback.bot.edit_message_text(
                chat_id=chat_id,
                message_id=rent_ui_message_id,
                text=err_text,
                parse_mode="HTML",
            )
        else:
            await callback.message.answer(err_text, parse_mode="HTML")

        await state.clear()
        return

    #!!!!!!!! жёсткий стоп: доменная проверка перед созданием записи в БД (двойная защита) !!!!!!!!!!!!!!!!!!!!!!!
    # тут не должен быть пользователь (кнопки нет), но это защита от: старых сообщений, параллельных кликов, гонок.
    item_id = rent_item["id"]
    try:
        await rental_service.ensure_item_available(item_id) # ищет открытую аренду по item_id
        # если не находит → просто делает return (возвращает управление обратно в confirm_rent без эффекта)
    except ItemNotAvailable as e:
        err_text = _format_item_not_available_message(e)
        if rent_ui_message_id:
            await callback.bot.edit_message_text(
                chat_id=chat_id,
                message_id=rent_ui_message_id,
                text=err_text,
                parse_mode="HTML",
            )
        else:
            await callback.message.answer(err_text, parse_mode="HTML")

        # await callback.answer() # нет! ты отправляешь новое сообщение -> Telegram сам уберёт “часики” при answer()
        await state.clear()
        return
    # !!!!!!!!!!!!

    # 2️⃣ Создаём сделку через сервис
    try:
        new_rental = await rental_service.create_rental(
            RentalCreate(
                item_id=rent_item["id"],
                renter_id=user.id,
                owner_id=rent_item["owner_id"],
                start_date=start_dt,
                end_date=end_dt,
                total_price=total_price,
                deposit_amount=rent_item.get("deposit_amount"),
                status=RentalStatus.REQUESTED, # Начальный статус
            )
        )
    except Exception as e:
        logger.exception(f"[Rent] Ошибка создания аренды: {e}")
        #await callback.message.edit_text(
        #    "❌ Не удалось создать запрос на аренду. Попробуйте позже."
        #)
        err_text = "❌ Не удалось создать запрос на аренду. Попробуйте позже."

        if rent_ui_message_id:
            await callback.bot.edit_message_text(
                chat_id=chat_id,
                message_id=rent_ui_message_id,
                text=err_text,
                parse_mode="HTML",
            )
        else:
            await callback.message.answer(err_text, parse_mode="HTML")

        await state.clear()
        return

    logger.info(f"[Rent] Создана аренда #{new_rental.id}")

    """ Обработка результата
    if new_rental:
        rental_id = new_rental.id
        logger.info(f"Создана запись аренды #{rental_id} пользователем {user.id}")
        
        # Обновляем статистику пользователя (опционально, можно оставить/убрать)
        if "user" in context.user_data:
            user_context_data = context.user_data["user"]
            user_context_data["items_rented"] = user_context_data.get("items_rented", 0) + 1
            user_context_data["total_savings"] = user_context_data.get("total_savings", 0) + rent_data['total_price']
            if user_context_data.get("items_rented", 0) == 1:
                user_context_data["achievement_first_rental_in"] = True
            if user_context_data.get("items_rented", 0) >= 5:
                user_context_data["achievement_5_rentals_in"] = True
    """

    # 3️⃣ Отображаем сообщение об успешном создании запроса
    text = (
        f"✅ <b>Запрос на аренду отправлен!</b>\n\n"
        f"📦 <b>{rent_item['name']}</b>\n"
        f"📅 {start_date} — {end_date}\n"
        f"⏱️ {days_count} дн.\n\n"
        f"💰 Стоимость: <b>{total_price} ₽</b>\n"
        f"🛡 Залог: <b>{rent_item.get('deposit_amount') or 'Нет'} ₽</b>\n\n"
        #f"💵 Итого: *{total_price}* ₽ + Залог: *{rent_item.get('deposit_amount') or 'Нет'}* ₽\n\n"
        f"ℹ️ Статус: <b>Ожидает подтверждения владельцем</b>\n\n"
        f"Вы получите уведомление, когда владелец ответит на ваш запрос."
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📋 Мои сделки", callback_data="rental_list")], # back_to_rentals
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main_menu")], # menu:main
        ]
    )

    #await callback.message.edit_text(
    #    text,
    #    reply_markup=keyboard,
    #    parse_mode="HTML"
    #)

    if rent_ui_message_id:
        await callback.bot.edit_message_text(
            chat_id=chat_id,
            message_id=rent_ui_message_id,
            text=text,
            reply_markup=keyboard,
            parse_mode="HTML",
        )
    else:
        await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")

    # 5️⃣ Чистим FSM
    await state.clear()


@rental_router.message(F.text == "📋 Мои сделки")
@rental_router.callback_query(F.data == "rental_list")
@rental_router.callback_query(F.data == "back_to_rentals")
async def view_my_rentals(event: Message | CallbackQuery, rental_service: RentalService,user):
    """Показывает список сделок пользователя"""

    #user_id = user.id
    logger.info(f"[Rentals] Пользователь {user.id} запросил список сделок")

    # Получаем сделки
    rentals = await rental_service.get_user_rentals(user.id) # Изменение 1

    # Если сделок нет
    if not rentals:
        text = "📭 У вас пока нет активных или завершённых сделок."
        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu:main")]
            ]
        )
        return await send_or_edit(event, text, markup)

    # Формируем текст
    text = "<b>📋 Ваши сделки</b>\n\n"

    # порядок статусов (Сортируем для удобства: сначала активные, потом остальные)
    status_order = {
        "ACTIVE": 1,
        "CONFIRMED": 2,
        "REQUESTED": 3,
        "COMPLETED": 10,
        "CANCELLED_BY_OWNER": 11,
        "CANCELLED_BY_RENTER": 12,
        "REJECTED_BY_OWNER": 13,
        "REJECTED_BY_RENTER": 14,
        "CANCELLED_CONFIRMED_BY_OWNER": 15,
        "CANCELLED_CONFIRMED_BY_RENTER": 16,
        "DISPUTED": 20,
    }

    status_labels = {
        "ACTIVE": "Активная аренда",
        "CONFIRMED": "Подтверждена владельцем",
        "REQUESTED": "Запрос отправлен",
        "COMPLETED": "Завершена",
        "CANCELLED_BY_OWNER": "Отклонена владельцем",
        "CANCELLED_BY_RENTER": "Отменена арендатором",
        "REJECTED_BY_OWNER": "Отменена владельцем (до начала)",
        "REJECTED_BY_RENTER": "Отменена арендатором (до начала)",
        "CANCELLED_CONFIRMED_BY_OWNER": "Отменена владельцем",
        "CANCELLED_CONFIRMED_BY_RENTER": "Отменена арендатором",
        "DISPUTED": "Спор",
    }

    """Тут надо переделать вывод статусов!!! Некоректно работает."""

    # сортировка
    rentals.sort(key=lambda r: status_order.get(r["status"], 99))

    keyboard = []
    for rental in rentals:
        #role_indicator = "➡️" if rental["user_role"] == "renter" else "⬅️"
        role_label = "Вы арендуете ➡️" if rental["user_role"] == "renter" else "Вы сдаёте ⬅️"

        start_date = rental['start_date']
        end_date = rental['end_date']
        if isinstance(start_date, str):
            start_date = datetime.fromisoformat(start_date)

        if isinstance(end_date, str):
            end_date = datetime.fromisoformat(end_date)

        status = rental["status"]
        status_label = status_labels.get(status, status)

        text += (
            f"• <b>Сделка #{rental['id']}</b>\n"
            f"  {role_label}\n"
            f"  📅 {start_date:%d.%m.%Y} — {end_date:%d.%m.%Y}\n"
            f"  🔖 Статус: <i>{status_label}</i>\n\n"
        )

        keyboard.append([
            InlineKeyboardButton(
                text=f"🔎 Детали сделки #{rental['id']}",
                callback_data=f"rental_details:{rental['id']}"
            )
        ])

    keyboard.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu:main")])
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

    # Ограничиваем длину сообщения, если оно слишком большое
    if len(text) > 3900:
        text = text[:3800] + "\n\n… список обрезан (очень много сделок)."

    return await send_or_edit(event, text, markup)

# ===================================================================================================

async def render_rental_details(callback: CallbackQuery, rental_service: RentalService, user, rental_id: int):
    # 1️⃣ Получаем детали сделки
    details = await rental_service.get_rental_details(rental_id=rental_id, current_user_id=user.id)
    if not details:
        await callback.message.answer("❌ Не удалось загрузить детали сделки или у вас нет доступа.")
        return

    # 2️⃣ Формируем текст
    # 3️⃣ Формируем кнопки в зависимости от статуса и роли
    text, markup = build_rental_details_ui(details)

    logger.info("статус аренды: rental_id=%s status=%s owner_id=%s actor=%s",
                rental_id, details["status"], details["owner"]["id"], user.id)

    # 4️⃣ Пытаемся редактировать сообщение, если нельзя — отправляем новое
    try:
        await callback.message.edit_text(text, reply_markup=markup, parse_mode="HTML")
    except TelegramBadRequest as e:
        # если сообщение уже нельзя редактировать или было не текстом: photo/caption
        if "message is not modified" in str(e).lower(): # Сообщение то же?
            return
        await callback.message.answer(text, reply_markup=markup, parse_mode="HTML")

@rental_router.callback_query(F.data.startswith("rental_details:"))
async def show_rental_details(callback: CallbackQuery, rental_service: RentalService, user):
    """Отображает детали конкретной аренды."""
    await callback.answer()

    try:
        rental_id = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        await callback.answer("Некорректная сделка.", show_alert=True)
        return
    logger.info(f"Пользователь {user.id} запросил детали сделки {rental_id}")

    await render_rental_details(callback, rental_service, user, rental_id)

# ============================== САМА СДЕЛКА МЕЖДУ ВЛАДЕЛЬЦЕМ И АРЕНДАТОРОМ ======================================================================
"""
Сделка всегда находится в одном статусе.
Переходы строго ограничены.

Никаких «если захотели — поменяли».

1. REQUESTED — «Запрос отправлен» (кто создает: арендатор - нажал «🤝 Арендовать»)

Что видит арендатор:
        Статус: ⏳ Ожидает подтверждения
        Кнопка: ❌ Отменить запрос

Что видит владелец:
        Новый запрос аренды
        Кнопки:
            ✅ Подтвердить
            ❌ Отклонить

Кто	   → Действие
OWNER  → CONFIRMED
OWNER  → REJECTED
RENTER → CANCELLED_BY_RENTER
-------------------------------------------

2. Переход: REQUESTED → CONFIRMED — «Подтверждено владельцем» (кто переводит: владелец)

Что видят оба:
        Даты аренды
        Контакт друг друга
        Статус: 🟢 Подтверждено
Кнопки:
    RENTER: ❌ Отменить (до начала)
    OWNER: ❌ Отменить (до начала)

Владелец согласился - Вещь «зарезервирована»
!Но что важно: Аренда еще не началась, это ожидание даты, т.е. перехода SYSTEM → ACTIVE
(начать аренду - сам бот автоматически)
-------------------------------------------

3. ACTIVE — «Аренда активна»
Переход: CONFIRMED → ACTIVE (Кто переводит: SYSTEM)
1) CONFIRMED: Владелец согласился (юридически/логически вы договорились)
2) ACTIVE: Фактическое пользование вещью началось (вещь передана, время пошло, депозит/оплата применились)

ACTIVE = “аренда идёт, вещь у арендатора, период считается, правила отмены/спора другие”

Чтобы ACTIVE означал реальный факт передачи, нам нужна “двухсторонняя фиксация”:
    владелец нажал «Передал вещь»
    арендатор нажал «Получил вещь»
    только когда оба события произошли → переводим в ACTIVE

В ACTIVE меняется всё:
    появляются основания для спора,
    отмена превращается в “разрыв активной аренды” (другие последствия),
    начинается (или считается) срок,
    можно “завершить” только после факта возврата.

Что видят оба:
    Статус: 🔵 Активна
    Дата окончания
Кнопки:
    🆘 Открыть спор (Сообщить о проблеме) 
    ❌ Досрочно завершить (опционально) - оба или только Владелец?

Переходы:
SYSTEM → COMPLETED (по end_date)
RENTER/OWNER → DISPUTED
-------------------------------------------

🟣 4. COMPLETED — «Завершена» (Кто переводит: SYSTEM \или\ OWNER подтвердил возврат)
Переход: ACTIVE → COMPLETED

Вещь возвращена
Финансы зафиксированы
Можно оставлять отзыв (👉 ТОЛЬКО здесь появляются отзывы)

Что видят оба:
    Статус: ✅ Завершена
    Кнопка: ⭐ Оставить отзыв (если не оставлен)
Переходы:
    нет (ФИНАЛ)
-------------------------------------------

🔴 5. REJECTED — «Отклонена» (кем: владельцем)
Переход: REQUESTED → REJECTED
Финал. Отзывов нет.

ЛИБО
⚫ 5.1. CANCELLED_BY_RENTER — «Отменено арендатором»
Переходы:
REQUESTED → CANCELLED_BY_RENTER
CONFIRMED → CANCELLED_BY_RENTER
ACTIVE → CANCELLED_BY_RENTER (опционально)

⚫ 5.2. CANCELLED_BY_OWNER — «Отменено владельцем»
Переходы:
REQUESTED → CANCELLED_BY_OWNER
CONFIRMED → CANCELLED_BY_OWNER
ACTIVE → CANCELLED_BY_OWNER (опционально)


⚠️ 8. DISPUTED — «Спор» (Кто: любой участник)
Когда: проблема во время ACTIVE

Что дальше:
    ручная обработка
    админ
    заморозка денег
"""

def _parse_rental_id(callback: CallbackQuery) -> int | None:
    """
    Ожидаем формат callback_data: rental_action:<action>:<rental_id>
    Возвращает rental_id или None (и сам показывает alert).
    """
    try: # ожидаем жёсткий формат: ["rental_action", "confirm", "<id>"] - rental_action:confirm:<id>
        parts = callback.data.split(":") # action = parts[1]
        return int(parts[2])
    except (IndexError, ValueError):
        return None


async def _run_rental_action(
    *,
    callback: CallbackQuery,
    rental_service,
    user,
    rental_id: int,
    service_call, # awaitable -> bool   # rental_service.confirm_requested(rental_id=rental_id, actor_id=user.id)
    ok_text: str, # "Подтверждено" из await callback.answer()
    fail_text: str, # fail_text = "Не удалось подтвердить (статус уже изменился или нет прав)."
    log_name: str, # по сути название функции, чтобы в лог вставить
) -> None:
    """
    Единая обвязка:
    - выполняет сервис-метод
    - обрабатывает исключения
    - показывает callback.answer()
    - перерисовывает детали (всегда после fail/ok, кроме crash)
    """

    try: # Вызов бизнес-логики: “Попробуй перевести сделку в STATUS, если это разрешено”
        ok = await service_call()
    except Exception: # Это НЕ бизнес-логика, а защита от: падения БД, таймаута и т.д.
        logger.exception("%s failed rental_id=%s user_id=%s", log_name, rental_id, user.id)
        await callback.answer("Ошибка. Попробуйте позже.", show_alert=True)
        return
    """Почему return сразу: мы не знаем, изменился ли статус / UI может стать ложным / нельзя продолжать
    Тут НЕ должно быть render_rental_details"""

    if not ok: # Бизнес-отказ (ok == False) - статус уже не REQUESTED | пользователь не владелец | другой пользователь успел раньше
        await callback.answer(fail_text, show_alert=True)
        # Почему здесь show_alert=True: пользователь ожидал действие → нужно явно объяснить, почему “не сработало”
        await render_rental_details(callback, rental_service, user, rental_id)
        # даже при fail — перерисуем, чтобы UI был актуальным и пользователь должен увидеть новый статус/новые кнопки
        return

    # Успешный сценарий
    await callback.answer(ok_text)

    # Перерисовка после успеха
    await render_rental_details(callback, rental_service, user, rental_id)

    """Эта функция и + _parse_rental_id():
        ✅ корректно обрабатывает все 3 типа ошибок
        ✅ не смешивает бизнес и инфраструктуру
        ✅ всегда приводит UI в актуальное состояние
    """

@rental_router.callback_query(F.data.startswith("rental_action:confirm:"))
async def rental_confirm(callback: CallbackQuery, rental_service, user):
    """Кнопка владельца “Подтвердить” (REQUESTED → CONFIRMED)"""

    rental_id = _parse_rental_id(callback)
    if rental_id is None:
        await callback.answer("Некорректная кнопка.", show_alert=True)
        return
    """Почему ТУТ только answer + return (в _parse_rental_id): мы ещё не знаем rental_id 
    (→ нельзя: звать сервис/перерисовывать UI)"""

    await _run_rental_action(
        callback=callback,
        rental_service=rental_service,
        user=user,
        rental_id=rental_id,
        service_call=lambda: rental_service.confirm_requested(rental_id=rental_id, actor_id=user.id),
        ok_text="Подтверждено",
        fail_text="Не удалось подтвердить (статус изменился или нет прав).",
        log_name="confirm_requested",
    )

    """confirm_requested() внутри: проверяет: существует ли сделка / является ли пользователь владельцем / 
    статус = REQUESTED / делает атомарный update / возвращает True-False"""

# Владелец отклонил запрос аренды
@rental_router.callback_query(F.data.startswith("rental_action:rejected_by_owner:"))
async def rental_reject_by_owner(callback: CallbackQuery, rental_service: RentalService, user):
    """Кнопка владельца “❌ Отклонить” (REQUESTED → REJECTED_BY_OWNER)"""
    rental_id = _parse_rental_id(callback)
    if rental_id is None:
        await callback.answer("Некорректная кнопка.", show_alert=True)
        return

    await _run_rental_action(
        callback=callback,
        rental_service=rental_service,
        user=user,
        rental_id=rental_id,
        service_call=lambda: rental_service.reject_requested_by_owner(rental_id=rental_id, owner_id=user.id),
        ok_text="Отклонено",
        fail_text="Не удалось отклонить (статус изменился или нет прав).",
        log_name="reject_requested_by_owner",
    )

# Арендатор отклонил свой запрос аренды
@rental_router.callback_query(F.data.startswith("rental_action:rejected_by_renter:"))
async def rental_reject_by_renter(callback: CallbackQuery, rental_service: RentalService, user):
    """Кнопка арендатора “❌ Отклонить” (REQUESTED → REJECTED_BY_RENTER)"""
    rental_id = _parse_rental_id(callback)
    if rental_id is None:
        await callback.answer("Некорректная кнопка.", show_alert=True)
        return

    await _run_rental_action(
        callback=callback,
        rental_service=rental_service,
        user=user,
        rental_id=rental_id,
        service_call=lambda: rental_service.reject_requested_by_renter(rental_id=rental_id, renter_id=user.id),
        ok_text="Запрос отменён",
        fail_text="Не удалось отменить (статус изменился или нет прав).",
        log_name="reject_requested_by_renter",
    )

# Владелец отменяет подтвержденную аренду
@rental_router.callback_query(F.data.startswith("rental_action:cancelled_confirmed_by_owner:"))
async def rental_cancel_confirmed_by_owner(callback: CallbackQuery, rental_service: RentalService, user):
    rental_id = _parse_rental_id(callback)
    if rental_id is None:
        await callback.answer("Некорректная кнопка.", show_alert=True)
        return

    await _run_rental_action(
        callback=callback,
        rental_service=rental_service,
        user=user,
        rental_id=rental_id,
        service_call=lambda: rental_service.cancel_confirmed_by_owner(rental_id=rental_id, owner_id=user.id),
        ok_text="Аренда отменена владельцем",
        fail_text="Не удалось отменить (статус изменился или нет прав).",
        log_name="cancel_confirmed_by_owner",
    )

# Арендатор отменяет подтвержденную аренду
@rental_router.callback_query(F.data.startswith("rental_action:cancelled_confirmed_by_renter:"))
async def rental_cancel_confirmed_by_renter(callback: CallbackQuery, rental_service: RentalService, user):
    rental_id = _parse_rental_id(callback)
    if rental_id is None:
        await callback.answer("Некорректная кнопка.", show_alert=True)
        return

    await _run_rental_action(
        callback=callback,
        rental_service=rental_service,
        user=user,
        rental_id=rental_id,
        service_call=lambda: rental_service.cancel_confirmed_by_renter(rental_id=rental_id, renter_id=user.id),
        ok_text="Аренда отменена арендатором",
        fail_text="Не удалось отменить (статус изменился или нет прав).",
        log_name="cancel_confirmed_by_renter",
    )

# Владелец отменяет активную аренду
@rental_router.callback_query(F.data.startswith("rental_action:cancelled_by_owner:"))
async def rental_cancel_active_by_owner(callback: CallbackQuery, rental_service: RentalService, user):
    """Владелец отменяет активную аренду"""
    rental_id = _parse_rental_id(callback)
    if rental_id is None:
        await callback.answer("Некорректная кнопка.", show_alert=True)
        return

    await _run_rental_action(
        callback=callback,
        rental_service=rental_service,
        user=user,
        rental_id=rental_id,
        service_call=lambda: rental_service.cancel_active_by_owner(rental_id=rental_id, owner_id=user.id),
        ok_text="Активная аренда отменена владельцем",
        fail_text="Не удалось отменить (статус изменился или нет прав).",
        log_name="cancel_active_by_owner",
    )

# Арендатор отменяет активную аренду
@rental_router.callback_query(F.data.startswith("rental_action:cancelled_by_renter:"))
async def rental_cancel_active_by_renter(callback: CallbackQuery, rental_service: RentalService, user):
    """Арендатор отменяет активную аренду"""
    rental_id = _parse_rental_id(callback)
    if rental_id is None:
        await callback.answer("Некорректная кнопка.", show_alert=True)
        return

    await _run_rental_action(
        callback=callback,
        rental_service=rental_service,
        user=user,
        rental_id=rental_id,
        service_call=lambda: rental_service.cancel_active_by_renter(rental_id=rental_id, renter_id=user.id),
        ok_text="Активная аренда отменена арендатором",
        fail_text="Не удалось отменить (статус изменился или нет прав).",
        log_name="cancel_active_by_renter",
    )


# ******************** это не статусы, а булевый флаг ***********
"""
Чтобы ACTIVE означал реальный факт передачи, нам нужна “двухсторонняя фиксация”:
    владелец нажал «Передал вещь»
    арендатор нажал «Получил вещь»
    только когда оба события произошли → переводим в ACTIVE

В ACTIVE меняется всё:
    появляются основания для спора,
    отмена превращается в “разрыв активной аренды” (другие последствия),
    начинается (или считается) срок,
    можно “завершить” только после факта возврата.
  
Архитектурно правильно: не плодить статусы (типа “owner_handed_over”), а хранить “подтверждения-флаги” 
отдельными полями в самой сделке.

И status желательно передавать как Enum, не как строку (чтобы UI работал типобезопасно):
    status: rental.status (Enum)
    status_value: rental.status.value (если нужно для текста)
"""
# “Передал вещь” (owner)
@rental_router.callback_query(F.data.startswith("rental_action:handover_owner:"))
async def rental_handover_owner(callback: CallbackQuery, rental_service: RentalService, user):
    rental_id = _parse_rental_id(callback)
    if rental_id is None:
        await callback.answer("Некорректная кнопка.", show_alert=True)
        return

    await _run_rental_action(
        callback=callback,
        rental_service=rental_service,
        user=user,
        rental_id=rental_id,
        service_call=lambda: rental_service.confirm_handover_by_owner(rental_id=rental_id, owner_id=user.id),
        ok_text="Отмечено: вещь передана",
        fail_text="Не удалось отметить (статус изменился / нет прав / уже отмечено).",
        log_name="handover_owner",
    )

# “Получил вещь” (renter)
@rental_router.callback_query(F.data.startswith("rental_action:receive_renter:"))
async def rental_receive_renter(callback: CallbackQuery, rental_service: RentalService, user):
    rental_id = _parse_rental_id(callback)
    if rental_id is None:
        await callback.answer("Некорректная кнопка.", show_alert=True)
        return

    await _run_rental_action(
        callback=callback,
        rental_service=rental_service,
        user=user,
        rental_id=rental_id,
        service_call=lambda: rental_service.confirm_receive_by_renter(rental_id=rental_id, renter_id=user.id),
        ok_text="Отмечено: вещь получена",
        fail_text="Не удалось отметить (статус изменился / нет прав / уже отмечено).",
        log_name="receive_renter",
    )

# по аналогии нужно будет добавить флаг ОПЛАТЫ
"""
Добавь в модель Rental
    payment_confirmed_at: datetime | None (или payment_status)


(позже) Оплата/холд: ✅/⏳
    
get_rental_details): (позже) payment_confirmed_at

- добавляешь поле payment_confirmed_at (или status)
- добавляешь кнопку/процесс оплаты в CONFIRMED
- в activate_if_ready добавляешь условие: payment_confirmed_at IS NOT NULL
"""
# **********************************************

# ✅ Завершить (owner)
@rental_router.callback_query(F.data.startswith("rental_action:complete:"))
async def rental_complete(callback: CallbackQuery, rental_service: RentalService, user):
    rental_id = _parse_rental_id(callback)
    if rental_id is None:
        await callback.answer("Некорректная кнопка.", show_alert=True)
        return

    await _run_rental_action(
        callback=callback,
        rental_service=rental_service,
        user=user,
        rental_id=rental_id,
        service_call=lambda: rental_service.complete_active(rental_id=rental_id, owner_id=user.id),
        ok_text="Аренда завершена",
        fail_text="Не удалось завершить (статус изменился или нет прав)",
        log_name="complete_active",
    )

# ⚠️ Открыть спор (owner/renter)
@rental_router.callback_query(F.data.startswith("rental_action:dispute:"))
async def rental_dispute(callback: CallbackQuery, rental_service: RentalService, user):
    rental_id = _parse_rental_id(callback)
    if rental_id is None:
        await callback.answer("Некорректная кнопка.", show_alert=True)
        return

    await _run_rental_action(
        callback=callback,
        rental_service=rental_service,
        user=user,
        rental_id=rental_id,
        service_call=lambda: rental_service.open_dispute(rental_id=rental_id, actor_id=user.id),
        ok_text="Спор открыт",
        fail_text="Не удалось открыть спор (статус изменился или нет прав)",
        log_name="open_dispute",
    )



# ✅ Обновляем UI: безопасно (иногда это caption/photo)
# await _safe_edit(callback, "✅ Заявка подтверждена владельцем.")
async def _safe_edit(callback: CallbackQuery, text: str, reply_markup=None):
    msg = callback.message
    try:
        if msg.text is not None:
            return await msg.edit_text(text, reply_markup=reply_markup, parse_mode="HTML")
        # если это фото/медиа с подписью
        return await msg.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="HTML")
    except TelegramBadRequest:
        # fallback: если редактирование невозможно — отправим новым сообщением
        return await msg.answer(text, reply_markup=reply_markup, parse_mode="HTML")

# =========================================== ОТЗЫВЫ =================================================
"""Базовые инварианты (очень важно)
1) Отзыв всегда привязан к сделке (rental)
2) Один пользователь → один отзыв в рамках одной сделки
3) Отзыв можно оставить только после завершения аренды
4) Рецензент и получатель — разные пользователи
5) Рейтинг строго 1–5
6) Отзыв нельзя изменить после публикации (можно расширить потом) 


@rental_router.callback_query(F.data.startswith("rental_action:review:"))
async def start_review_process(
    callback: CallbackQuery,
    state: FSMContext,
    review_service: ReviewService,
    rental_service: RentalService,
    user,
):
    await callback.answer()

    rental_id = int(callback.data.split(":")[1])

    try:
        rental = await rental_service.get_by_id(rental_id)
        if not rental:
            await callback.message.answer("❌ Сделка не найдена")
            return

        # сервис сам проверит:
        # - сделка завершена
        # - пользователь участник
        # - отзыв ещё не оставлен

        # определяем роли
        if user.id == rental.renter_id:
            reviewee_id = rental.owner_id # "reviewer_role" - собственник
        elif user.id == rental.owner_id:
            reviewee_id = rental.renter_id # "reviewer_role" - покупатель
        else:
            await callback.message.answer("❌ Вы не участник этой сделки")
            return

        await state.update_data(
            rental_id=rental_id,
            reviewer_id=user.id,
            reviewee_id=reviewee_id,
        )

        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(text="⭐"),
                    KeyboardButton(text="⭐⭐"),
                    KeyboardButton(text="⭐⭐⭐"),
                    KeyboardButton(text="⭐⭐⭐⭐"),
                    KeyboardButton(text="⭐⭐⭐⭐⭐"),
                ],
                [KeyboardButton(text="❌ Отмена")],
            ],
            resize_keyboard=True,
        )

        text = "📊 *Оставить отзыв*\n\n Оцените опыт аренды по шкале от 1 до 5 звезд:"
        await callback.message.answer(
            text=text,
            reply_markup=keyboard,
        )

        await state.set_state(ReviewStates.rating)

    except Exception as e:
        await callback.message.answer(str(e))

# Обработка выбора рейтинга
@rental_router.callback_query(ReviewStates.rating, F.data.startswith("review_rating:"))
async def process_review_rating(
    callback: CallbackQuery,
    state: FSMContext,
):
    await callback.answer()

    rating = int(callback.data.split(":")[1])

    data = await state.get_data()
    review_context = data["review_context"]

    review_context["rating"] = rating
    await state.update_data(review_context=review_context)

    await state.set_state(ReviewStates.comment)

    await callback.message.edit_text(
        f"⭐ Оценка: <b>{rating}</b>\n\n"
        "💬 Напишите комментарий или нажмите «Пропустить».",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Пропустить", callback_data="review_skip_comment")],
                [InlineKeyboardButton(text="❌ Отмена", callback_data="review_cancel")],
            ]
        ),
        parse_mode="HTML",
    )

# Пропуск комментария
@rental_router.callback_query(ReviewStates.comment, F.data == "review_skip_comment")
async def skip_review_comment(
    callback: CallbackQuery,
    state: FSMContext,
    review_service: ReviewService,
):
    await callback.answer()

    data = await state.get_data()
    ctx = data["review_context"]

    try:
        await review_service.create_review(
            ReviewCreate(
                rental_id=ctx["rental_id"],
                reviewer_id=ctx["reviewer_id"],
                reviewee_id=ctx["reviewee_id"],
                rating=ctx["rating"],
                comment=None,
            )
        )
    except Exception as e:
        await callback.message.answer(f"❌ {e}")
        return

    await state.clear()

    await callback.message.edit_text(
        "✅ <b>Отзыв сохранён</b>\n\nСпасибо за ваш отзыв!",
        parse_mode="HTML",
    )

# Отмена
@rental_router.callback_query(F.data == "review_cancel")
async def cancel_review(
    callback: CallbackQuery,
    state: FSMContext,
):
    await callback.answer()
    await state.clear()

    await callback.message.edit_text(
        "❌ Оставление отзыва отменено.",
        parse_mode="HTML",
    )

"""
