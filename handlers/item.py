import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest

from services.item_service import ItemService
from services.photo_service import PhotoService
from services.category_service import CategoryService
from services.user_service import UserService
from utils.functions import format_price

from states.item import ItemCreateStates
from keyboards.main_kb import get_back_inline_keyboard, build_category_keyboard
from keyboards.item_kb import get_photos_keyboard
from utils.messages import format_step

logger = logging.getLogger(__name__)

items_router = Router(name="items")

# Константы callback-данных
CAT_FI_PREFIX = "cat_for_item:"
SUBCAT_FI_PREFIX = "subcat_for_item:"

BACK_TO_MENU_CB = "back_to_main_menu"
ALL_CATEGORY_CB = "all_cat"
BACK_TO_CAT = "back_to_categories"

MAX_PHOTOS = 5

@items_router.message(F.text == "📦 Мои объявления")
@items_router.callback_query(F.data == "my_items")
async def show_my_items(
    event: Message | CallbackQuery,
    #state: FSMContext,
    item_service: ItemService
):
    """Показывает список объявлений пользователя"""

    user_id = event.from_user.id
    logger.info(f"[DEBUG] Вызвана show_my_items для user_id={user_id}")

    try:
        # Получаем объявления из сервиса
        items = await item_service.list_by_user(user_id)

        if not items:
            logger.info(f"[DEBUG] У пользователя {user_id} нет объявлений.")

            keyboard = [
                [InlineKeyboardButton(text="➕ Добавить объявление", callback_data="add_item")],
                [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="back_to_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

            message_text = (
                "📦 <b>Мои объявления</b>\n\n"
                "У вас пока нет активных объявлений.\n"
                "Создайте новое объявление, чтобы сдать вещи в аренду!"
            )

            if isinstance(event, Message):
                await event.answer(message_text, reply_markup=reply_markup)
            else:
                await event.message.edit_text(message_text, reply_markup=reply_markup)
                await event.answer()
            return

        # Если у пользователя есть объявления (Тут по имени отсев, но потом надо по id)
        keyboard = [
            [InlineKeyboardButton(text="➕ Добавить объявление", callback_data="add_item")]
        ]
        for item in items: # Добавляем кнопки для каждого объявления
            status = "✅ Активно" if item.is_available else "❌ Не активно"
            keyboard.append([
                InlineKeyboardButton(
                    text=f"{item.title} ({status})",
                    callback_data=f"show_item:{item.id}"
                )
            ])
        keyboard.append([InlineKeyboardButton(text="🔙 Назад в меню", callback_data="back_to_menu")])

        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

        message_text = (
            "📦 <b>Мои объявления</b>\n\n"
            f"У вас {len(items)} {get_items_count_str(len(items))}.\n"
            "Выберите объявление для просмотра или редактирования:"
        )

        if isinstance(event, Message):
            await event.answer(message_text, reply_markup=reply_markup)
        else:
            await event.message.edit_text(message_text, reply_markup=reply_markup)
            await event.answer()

    except Exception as e:
        logger.error(f"Ошибка при получении объявлений: {e}", exc_info=True)

        error_text = "❌ Произошла ошибка. Пожалуйста, попробуйте позже."
        if isinstance(event, Message):
            await event.answer(error_text)
        else:
            await event.answer(error_text, show_alert=True)

        # Можно вернуть в главное меню
        # from handlers.base import show_main_menu
        # return await show_main_menu(event, state)


@items_router.callback_query(F.data.startswith("show_item:"))
async def show_item_details(callback: CallbackQuery, state: FSMContext,
    item_service: ItemService, category_service: CategoryService):
    """Показывает детали объявления"""
    try:
        logger.info("[DEBUG] Попали в show_item_details через кнопку")
        await callback.answer()

        # Извлекаем ID объявления
        item_id = callback.data.split(":")[1]
        await state.update_data(selected_item_id=item_id)

        # Получаем объявление
        item = await item_service.get_item_by_id(int(item_id))  # тут уже из БД, не demo
        if not item:
            await callback.answer("Объявление не найдено", show_alert=True)
            await show_my_items(callback, item_service) #  state,

        # --- Получаем категорию и подкатегорию ---
        category = await category_service.get_category(item.category_id) if item.category_id else None
        subcategory = await category_service.get_category(item.subcategory_id) if item.subcategory_id else None

        # --- Формируем текст с деталями ---
        item_details = (
            f"📦 *{item.title or 'Без названия'}*\n\n"
            f"📝 *Описание:*\n{item.description or 'Нет описания'}\n\n"
        )

        if category:
            item_details += f"🏷️ *Категория:* {category.name}"
            if subcategory:
                item_details += f" > {subcategory.name}\n"
            else:
                item_details += "\n"

        item_details += (
            f"💰 *Цена:* {format_price(item.price)}/день\n"
            f"🔐 *Залог:* {format_price(item.deposit_amount or 0)}\n"
        )

        min_days = item.min_rent_days or 1
        item_details += f"🕒 *Минимальный срок аренды:* {min_days} {get_days_str(min_days)}\n"

        if item.location:
            item_details += f"📍 *Местоположение:* {item.location}\n"

        status = "✅ Доступно для аренды" if item.is_available else "❌ Временно недоступно"
        item_details += f"✅ *Статус:* {status}\n\n"

        # --- Клавиатура действий ---
        keyboard: list[list[InlineKeyboardButton]] = []

        # Переключатель статуса
        if item.is_available:
            keyboard.append([InlineKeyboardButton(text="❌ Сделать недоступным", callback_data=f"toggle_available:{item.id}")])
        else:
            keyboard.append([InlineKeyboardButton(text="✅ Сделать доступным", callback_data=f"toggle_available:{item.id}")])

        # Редактирование и удаление
        keyboard.append([
            InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit_item:{item.id}"),
            InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"delete_item:{item.id}")
        ])

        # Назад
        keyboard.append([InlineKeyboardButton(text="🔙 Назад к списку", callback_data="my_items")])

        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

        # Отправляем результат
        await callback.message.edit_text(item_details, reply_markup=reply_markup, parse_mode="HTML")

    except Exception as e:
        logger.error(f"Ошибка при показе деталей объявления: {e}", exc_info=True)
        await callback.answer("Произошла ошибка. Попробуйте позже", show_alert=True)
        await show_my_items(callback, item_service) # state,

#===========================================Кнопка "Добавить объявление"==============================================
"""
Начинает процесс создания объявления (оба сценария: с категорией и без неё)

Сценарий 1 (главное меню «📦 Сдать в аренду»): event = Message             (вызов в base.py)
    — категории ещё нет → сразу просим название и ставим FSM на title.
    (категория/подкатегория пока неизвестны → просто создаём болванку и просим название)

Сценарий 2 (после выбора подкатегории): event = CallbackQuery с data вида "subcat:<id>"
    — извлекаем subcategory_id, берём category по parent_id, сохраняем в FSM и просим название.
    
    «➕ Добавить объявление» (inline-кнопка внутри списка «Мои объявления»)
"""

# ========================================= СЦЕНАРИЙ 2 (Callback)  =====================================================
@items_router.callback_query(F.data == "add_item")
async def start_create_item_from_my_items(
    callback: CallbackQuery,
    state: FSMContext,
    category_service: CategoryService
):
    """Запуск процесса создания объявления из списка 'Мои объявления'

    Создаёт новый контекст FSM, подготавливает new_item и показывает категории.
    """
    await callback.answer()
    logger.debug("[FSM] Загружаем список категорий для создания объявления…")
    # 🔄 Очистим предыдущие данные (если пользователь случайно не завершил прошлую FSM)
    await state.clear()

    # 💾 Инициализация FSM
    await state.update_data(
        mode="create_item",
        user_id=callback.from_user.id,
        new_item={
            "user_id": callback.from_user.id,
            "is_available": True,
            "is_featured": False,
            "min_rental_period": 1,
            "views_count": 0,
            "orders_count": 0,
        }, # данные которые можно заполнить сразу
    )

    # Переводим FSM в первое состояние - выбор категории
    await state.set_state(ItemCreateStates.category)
    logger.debug(f"[FSM] Запущено создание объявления. Состояние: {await state.get_state()}")

    # ⚙️ Получаем категории
    try:
        categories = await category_service.list_main() or []
    except Exception as e:
        logger.error("start_create_item_from_my_items(): не удалось получить категории: %s", e, exc_info=True)
        await callback.message.answer("⚠️ Не удалось загрузить категории. Попробуйте позже.")
        #categories = []
        return

    # 🧱 Формируем клавиатуру
    keyboard = build_category_keyboard(
        categories,
        prefix=CAT_FI_PREFIX,
        extra_buttons=[
            [InlineKeyboardButton(text="🔙 Назад в меню", callback_data=BACK_TO_MENU_CB)]
        ]
    )

    message_text = "📦 <b>Сдать в аренду</b>\n\nВыберите категорию для вашего объявления:"

    try:
        await callback.message.edit_text(message_text, reply_markup=keyboard, parse_mode="HTML")
    # Если сообщение уже не существует (например, пользователь удалил старое сообщение), бот может выбросить ошибку
    except TelegramBadRequest:
        await callback.message.answer(message_text, reply_markup=keyboard, parse_mode="HTML")


@items_router.callback_query(F.data.startswith("cat_for_item:"))
async def show_subcategories_for_creating_item(callback: CallbackQuery, state: FSMContext, category_service: CategoryService):
    """Показывает подкатегории для FSM-сценария 'Создать объявление'."""
    await callback.answer()
    category_id = int(callback.data.split(":")[1])
    await state.update_data(selected_category_id=category_id)

    category = await category_service.get_category(category_id)

    subcategories = await category_service.list_subcategories(category_id)
    if not subcategories:
        await callback.message.answer("⚠️ В категории пока нет подкатегорий.") # , reply_markup=reply_markup
        return

    keyboard = build_category_keyboard(
        subcategories,
        prefix=SUBCAT_FI_PREFIX,
        extra_buttons=[
            [InlineKeyboardButton(text="🔙 Назад к категориям", callback_data="create_back_to_cat")]
        ]
    )

    text = (
        f"📦 <b>Выбор категории для объявления</b>\n\n"
        f"Выбрана категория: <b>{category.name}</b>\n"
        f"Уточните подкатегорию:"
    )

    await callback.message.edit_text(
        text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )

    # FSM пока остаётся в состоянии category
    # Переход произойдёт позже — при выборе конкретной подкатегории


@items_router.callback_query(F.data.startswith("subcat_for_item:"))
async def start_create_item_from_subcategory(callback: CallbackQuery, state: FSMContext, category_service: CategoryService):
    """Переход из подкатегории к вводу названия вещи."""
    await callback.answer()

    # пробуем достать категорию из state
    data = await state.get_data()
    category_id = data.get("selected_category_id")
    category_name = data.get("selected_category_name", "Не выбрана")
    logger.info(f"[DEBUG] Категория и ее имя {category_id} и {category_name}")

    subcategory_id = None
    try:
        subcategory_id = int(callback.data.split(":")[1])
        await state.update_data(selected_subcategory_id=subcategory_id)
    except (IndexError, ValueError):
        await callback.message.edit_text("❌ Не удалось распознать подкатегорию.")


    category = await category_service.get_category(category_id) # if category_id else None
    subcategory = await category_service.get_category(subcategory_id) # if subcategory_id else None

    if not category or not subcategory:
        logger.warning("[DEBUG] ❌ Категория или подкатегория не найдена")
        await callback.message.answer(
            "❌ Категория|подкатегория не выбрана. Пожалуйста, выберите категорию|подкатегорию для вашего объявления."
        )
        from handlers.category import show_categories
        await show_categories(callback, category_service) # state, for_search=False

    # обновляем FSM данными
    new_item = data.get("new_item", {})
    # Обновляем только нужные поля
    new_item.update({
        "category_id": category.id,
        "subcategory_id": subcategory.id,
    })

    await state.update_data(
        selected_category_id=category.id,
        selected_category_name=category.name,
        selected_subcategory_name=subcategory.name,
        # new_item={
        # "user_id": event.from_user.id,
        #    "category_id": category.id,
        #    "subcategory_id": subcategory.id,
        # "is_available": True,
        # "is_featured": False,
        # "min_rental_period": 1,
        # "views_count": 0,
        # "orders_count": 0,
        # }
        new_item=new_item  # сохраняем обновлённый словарь обратно
    )

    # теперь просто вызываем "логический" шаг FSM
    await start_create_item_title(callback, state, category, subcategory)


# =================================== СЦЕНАРИЙ 1 (Message) ==========================================
async def start_create_item_from_menu(
        message: Message,
        state: FSMContext,
        user_service: UserService,
):
    # чистим state от старого
    try:
        await state.clear()
    except Exception as e:
        logger.warning(f"[FSM] Не удалось очистить state: {e}")

    # очищаем только данные (без сброса FSM)
    #await state.update_data({})
    tg_id = message.from_user.id
    user = await user_service.get_by_telegram_id(tg_id)

    await state.update_data(
        new_item={
            "user_id": user.id, #message.from_user.id,
            "category_id": 999,         # 🔹 временная заглушка
            "subcategory_id": 999,      # 🔹 временная заглушка
            "is_available": True,
            "is_featured": False,
            "min_rental_period": 1,
            "views_count": 0,
            "orders_count": 0,
        }
    )

    # теперь просто вызываем "логический" шаг FSM — без UI
    await start_create_item_title(message, state)


# Обработка ввода названия вещи (# Тут начинается FSM!)
async def start_create_item_title(event: Message | CallbackQuery, state: FSMContext, category=None, subcategory=None):
    """Показывает пользователю приглашение ввести название вещи."""

    logger.info(f"[FSM] → Старт создания объявления ({'из меню' if category is None else 'из подкатегории'})")

    cat_text = f"Категория: <b>{category.name}</b>\n" if category else ""
    subcat_text = f"Подкатегория: <b>{subcategory.name}</b>\n" if subcategory else ""
    text = (
        "📦 <b>Ваше новое объявление</b>\n\n"
        f"{cat_text}{subcat_text}\n"
        "📝 Введите название вещи:"
    )

    if isinstance(event, CallbackQuery):
        try:
            await event.message.edit_text(text, reply_markup=get_back_inline_keyboard(), parse_mode="HTML")
        except TelegramBadRequest:
            await event.message.answer(text, reply_markup=get_back_inline_keyboard(), parse_mode="HTML")
    else:
        await event.answer(text, reply_markup=get_back_inline_keyboard(), parse_mode="HTML")

    # переводим FSM в состояние ожидания названия
    await state.set_state(ItemCreateStates.title)
    logger.debug(f"[FSM] Установлено состояние: {await state.get_state()}")


@items_router.message(ItemCreateStates.title)
async def process_item_title(message: Message, state: FSMContext):
    """Обрабатывает ввод названия при создании объявления"""

    title = message.text.strip()

    if len(title) < 3:
        text = format_step("❌ Название слишком короткое. Пожалуйста, введите не менее 3 символов.",
                           1, 6)

        await message.answer(text, reply_markup=get_back_inline_keyboard(), parse_mode="HTML")
        return  # остаёмся в том же состоянии (title)

    if len(title) > 100:
        text = format_step("❌ Название слишком длинное. Пожалуйста, введите не более 100 символов.",
                          1, 6)
        await message.answer(text, reply_markup=get_back_inline_keyboard(), parse_mode="HTML")
        return  # остаёмся в том же состоянии (title)

    # сохраняем во временное хранилище FSM
    data = await state.get_data()
    new_item = data.get("new_item", {})
    new_item["title"] = title
    await state.update_data(new_item=new_item)
    logger.info(f"[FSM] Название сохранено: {title}")

    # запрашиваем описание
    description = ("📋 *Описание объявления* ✍️\n\n"
        "Пожалуйста, введите подробное описание вещи. Укажите:\n"
        "- Состояние и особенности\n"
        "- Комплектацию\n"
        "- Особенности использования\n"
        "- Другую важную информацию")


    await message.answer(
        format_step(description,2, 6),
        parse_mode="HTML",
        reply_markup=get_back_inline_keyboard("back_to_item_title")
    )
    # "back_to_item_title" - нужен хэндлер для него
    # back_to_item_title → возврат на шаг названия вещи, а не в меню! Мб это и не нужно

    print(">>> FSM ACTIVE:", await state.get_state())

    # переводим FSM в следующее состояние
    await state.set_state(ItemCreateStates.description)


@items_router.message(ItemCreateStates.description)
async def process_item_description(message: Message, state: FSMContext):
    """Обрабатывает ввод описания объявления"""

    description = message.text.strip()

    # Проверка длины
    if len(description) < 10:
        text = format_step("❌ Описание слишком короткое. Пожалуйста, введите более подробное описание (минимум 10 символов)",
                2, 6)

        await message.answer(text, reply_markup=get_back_inline_keyboard("back_to_item_title"), parse_mode="HTML")
        return  # остаёмся в состоянии description

    # Сохраняем описание в FSM
    data = await state.get_data()
    new_item = data.get("new_item", {})
    new_item["description"] = description
    await state.update_data(new_item=new_item)
    logger.info(f"[FSM] Описание сохранено: {description[:40]}...")

    # Переход к следующему шагу
    price_mes = ("💰 *Цена аренды*\n\n"
        "Укажите стоимость аренды за один день (только число).\n"
        "Например: 500")
    #"Укажите стоимость аренды в формате '500 руб/день' или '100 руб/час':"


    await message.answer(
        format_step(price_mes,3, 6),
        parse_mode="HTML",
        reply_markup=get_back_inline_keyboard("back_to_item_description")
    )

    await state.set_state(ItemCreateStates.price)


@items_router.message(ItemCreateStates.price)
async def process_item_price(message: Message, state: FSMContext):
    """Обрабатывает ввод цены аренды (шаг FSM)"""

    price_text = message.text.strip()

    try:
        # Преобразуем введённое значение в число
        price = float(price_text.replace(",", "."))
        if price <= 0:
            text = format_step(
                    "❌ Цена должна быть положительным числом.",
                    3, 6)

            await message.answer(
                text,
                reply_markup=get_back_inline_keyboard("back_to_item_description"),
                parse_mode="HTML"
            )
            return  # остаёмся в том же состоянии (price)

    except ValueError:
        await message.answer(
            format_step("❌ Некорректное значение.\nВведите цену — только число, больше 0.",
                        3, 6),
            reply_markup=get_back_inline_keyboard("back_to_item_description"),
        )
        return  # остаёмся в том же состоянии (price)

    # Сохраняем цену в FSM
    data = await state.get_data()
    new_item = data.get("new_item", {})
    new_item["price"] = price
    await state.update_data(new_item=new_item)
    logger.info(f"[FSM] Цена аренды сохранена: {price}")

    # Переходим к следующему шагу FSM — залог
    deposit_mes = ("🔐 *Залог*\n\n"
        "Укажите сумму залога (только число).\n"
        "💡 Залог возвращается после возврата вещи в исходном состоянии.\n"
        "Например: 5000")

    await message.answer(
        format_step(deposit_mes,4, 6),
        parse_mode="HTML",
        reply_markup=get_back_inline_keyboard("back_to_item_description")
    )

    await state.set_state(ItemCreateStates.deposit)


@items_router.message(ItemCreateStates.deposit)
async def process_item_deposit(message: Message, state: FSMContext):
    """Обрабатывает ввод суммы залога (шаг FSM)."""

    deposit_text = message.text.strip()

    try:
        # Преобразуем введённое значение в число
        deposit = float(deposit_text.replace(",", "."))
        if deposit < 0:
            text = format_step(
                "❌ Сумма залога не может быть отрицательной.",
                4, 6)
            await message.answer(
                text,
                reply_markup=get_back_inline_keyboard("back_to_item_price"),
                parse_mode="HTML"
            )
            return  # остаёмся в состоянии deposit

    except ValueError:
        text = format_step(
            "❌ Некорректное значение. Пожалуйста, введите число.",
            4, 6)
        await message.answer(
            text,
            reply_markup=get_back_inline_keyboard("back_to_item_price"),
            parse_mode="HTML"
        )
        return  # остаёмся в состоянии deposit

    # Сохраняем сумму залога в FSM
    data = await state.get_data()
    new_item = data.get("new_item", {})
    new_item["deposit"] = deposit
    await state.update_data(new_item=new_item)
    logger.info(f"[FSM] Сумма залога сохранена: {deposit}")

    # Переходим к следующему шагу FSM (местоположение)
    place_mes = ("📍 *Местоположение*\n\n"
        "Укажите, где находится вещь (город, район, метро и т.д.).\n"
        "Эта информация будет видна потенциальным арендаторам.")

    await message.answer(
        format_step(place_mes,5, 6),
        parse_mode="HTML",
        reply_markup=get_back_inline_keyboard("back_to_item_description")
    )

    await state.set_state(ItemCreateStates.location)


@items_router.message(ItemCreateStates.location)
async def process_item_location(message: Message, state: FSMContext):
    """Обрабатывает ввод местоположения вещи (шаг FSM)."""

    location = message.text.strip()

    # Проверяем длину ввода
    if len(location) < 3:
        text = format_step(
            "❌ Местоположение слишком короткое. "
            "Пожалуйста, укажите хотя бы город или район.",
            5, 6)
        await message.answer(
            text,
            reply_markup=get_back_inline_keyboard("back_to_item_deposit"),
            parse_mode="HTML"
        )

        return  # остаёмся в состоянии location

    # Сохраняем местоположение в FSM
    data = await state.get_data()
    new_item = data.get("new_item", {})
    new_item["location"] = location
    await state.update_data(new_item=new_item)
    logger.info(f"[FSM] Местоположение сохранено: {location}")

    # Переходим к следующему шагу FSM — минимальный срок аренды
    min_period_mes = ("⏱️ <b>Отлично!</b>\n\n"
        "Теперь укажите <b>минимальный срок аренды</b>.\n"
        "Например: <code>1 день</code>, <code>3 часа</code>, <code>2 недели</code>.")

    await message.answer(
        format_step(min_period_mes,6, 6),
        parse_mode="HTML",
        reply_markup=get_back_inline_keyboard("back_to_item_location")
    )

    await state.set_state(ItemCreateStates.rental_period)


@items_router.message(ItemCreateStates.rental_period)
async def process_item_rental_period(message: Message, state: FSMContext):
    """Обрабатывает ввод минимального срока аренды и показывает итоговое подтверждение объявления"""

    rental_period = message.text.strip()

    # Минимальная валидация — просто чтобы не было ерунды
    if len(rental_period) < 2:
        text = format_step(
            "❌ Слишком короткое значение. Укажите, например: <b>1 день</b> или <b>3 часа</b>.",
            6, 6)
        await message.answer(
            text,
            reply_markup=get_back_inline_keyboard("back_to_item_location"),
            parse_mode="HTML"
        )
        return  # остаёмся в состоянии rental_period

    # Сохраняем срок в FSM
    data = await state.get_data()
    new_item = data.get("new_item", {})
    new_item["rental_period"] = rental_period
    await state.update_data(new_item=new_item)

    logger.info(f"[FSM] Минимальный срок аренды сохранён: {rental_period}")

    # Переход к шагу загрузки фото
    await message.answer(
        "📸 Теперь загрузите фотографии вещи.\n"
        "Можно загрузить до 5 штук.\n"
        "Когда закончите — нажмите <b>«Готово»</b>.",
        reply_markup=get_photos_keyboard(),
        parse_mode="HTML",
    )

    await state.set_state(ItemCreateStates.photos)

# ============================================== ЛОГИКА ДОБАВЛЕНИЯ ФОТОГРАФИЙ ===========================================================
@items_router.message(ItemCreateStates.photos, F.text == "🔙 Назад")
async def photos_back(message: Message, state: FSMContext):
    """Возврат к предыдущему шагу (например, к описанию)."""
    await message.answer("Возвращаемся назад. Введите описание товара:",
                         reply_markup= get_back_inline_keyboard("back_to_item_rental_period")) # ???
    await state.set_state(ItemCreateStates.description)

@items_router.message(ItemCreateStates.photos, F.text == "✅ Готово")
async def photos_done(message: Message, state: FSMContext):
    """Пользователь завершил загрузку фотографий."""
    data = await state.get_data()
    photos = data.get("photos", [])

    if not photos:
        await message.answer(
            "⚠️ Вы не загрузили ни одной фотографии.\n"
            "Вы можете продолжить, но объявление будет без фото.",
        )

    # Вставляем фото в new_item, чтобы confirmation видела их
    new_item = data.get("new_item", {})
    new_item["photos"] = photos
    await state.update_data(new_item=new_item)

    # Переходим к финальному подтверждению
    await show_item_confirmation(message, new_item)

    await state.set_state(ItemCreateStates.confirmation)

async def show_item_confirmation(message: Message, item: dict):
    """Показывает итоговое подтверждение объявления."""

    name = item.get("title", "Без названия")
    description = item.get("description", "Нет описания")
    price = item.get("price", 0)
    deposit = item.get("deposit", 0)
    location = item.get("location", "Не указано")
    rental_period = item.get("rental_period", "Не указано")
    photos = item.get("photos", [])

    confirmation_text = (
        f"📦 <b>Подтверждение объявления</b>\n\n"
        f"📝 <b>Название:</b> {name}\n"
        f"📋 <b>Описание:</b> {description[:120]}{'...' if len(description) > 120 else ''}\n"
        f"💰 <b>Цена:</b> {price} ₽/день\n"
        f"🔐 <b>Залог:</b> {deposit} ₽\n"
        f"📍 <b>Местоположение:</b> {location}\n"
        f"⏱️ <b>Мин. срок аренды:</b> {rental_period}\n"
        f"📸 <b>Фотографий:</b> {len(photos)}\n\n"
        f"Всё верно? Подтвердите создание объявления 👇"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Разместить объявление", callback_data="publish_item")],
            [InlineKeyboardButton(text="❌ Удалить объявление", callback_data="cancel_item")], # back_to_menu
        ]
    )

    # Если есть фото — отправляем фото, либо просто текст
    if photos:
        try:
            await message.answer_photo(
                photo=photos[0],
                caption=confirmation_text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            return # ?
        except Exception as e:
            logger.warning(f"Не удалось отправить фото: {e}")

    # Отправляем текст
    await message.answer(
        confirmation_text,
        reply_markup=keyboard,
        parse_mode="HTML",
    )

@items_router.message(ItemCreateStates.photos, F.photo)
async def process_item_photos(message: Message, state: FSMContext):
    """Обработка загруженной фотографии."""

    data = await state.get_data()
    photos = data.get("photos", [])

    if len(photos) >= MAX_PHOTOS:
        await message.answer(
            f"⚠️ Вы уже загрузили максимальное количество фотографий ({MAX_PHOTOS}).\n"
            f"Нажмите «Готово», чтобы продолжить.",
            reply_markup=get_photos_keyboard()
        )
        return

    # # Получаем файловый ID фотографии с наилучшим разрешением
    file_id = message.photo[-1].file_id

    # Добавляем фото в список
    photos.append(file_id)
    await state.update_data(photos=photos)

    await message.answer(
        f"📸 Фото загружено! ({len(photos)}/{MAX_PHOTOS})\n"
        "Отправьте ещё фото или нажмите «Готово».",
        reply_markup=get_photos_keyboard()
    )
        #f"✅ Фотография #{len(photos)} загружена.\n"
        #f"Вы можете загрузить еще {5 - len(photos)} фото или нажать 'Готово'."

@items_router.message(ItemCreateStates.photos)
async def photos_wrong_input(message: Message):
    """Обработка неверного ввода (не фото и не команда)."""
    await message.answer(
        "❌ Пожалуйста, отправьте фотографию.\n"
        "Или нажмите «Готово».",
        reply_markup=get_photos_keyboard(), # ✅ Готово / 🔙 Назад   (reply keyboard)
    )
# =========================================================================================================

# ✅ Обработка подтверждения публикации объявления
@items_router.callback_query(F.data.in_({"publish_item", "edit_item", "cancel_item"}))
async def process_item_confirmation(
    callback: CallbackQuery,
    state: FSMContext,
    item_service: ItemService,
    photo_service: PhotoService,
):
    """Обрабатывает подтверждение создания (или отмену) объявления"""

    await callback.answer()  # убираем "часики"
    action = callback.data

    # достаём из FSM текущие данные объявления
    data = await state.get_data()
    new_item = data.get("new_item")
    photos: list[str] = data.get("photos", [])

    if not new_item:
        await callback.message.answer("❌ Не удалось найти данные объявления.")
        #from handlers.base import show_main_menu
        #await show_main_menu(callback.message, state)
        return

    # 🔥 1. ПУБЛИКАЦИЯ ОБЪЯВЛЕНИЯ
    if action == "publish_item":
        try:
            # 1️⃣ создаём объявление
            new_item["status"] = "PENDING" # NEW (Admin logic)
            created_item = await item_service.create(new_item) # create(ItemCreate(**new_item))
            item_id = created_item.id
            logger.info(f"[FSM] Объявление создано: id={item_id}, title={created_item.title}")

            # 2️⃣ сохраняем фотографии
            if photos:
                try:
                    await photo_service.add_photos(item_id, photos)
                    logger.info(f"[FSM] Сохранено {len(photos)} фото для item_id={item_id}")
                except Exception as e:
                    logger.error(f"[FSM] Ошибка сохранения фото для item_id={item_id}: {e}")

            # 3️⃣ сообщение пользователю
            await callback.message.answer(
                f"✅ <b>Поздравляем!</b>\n\n"
                f"Ваше объявление <b>«{created_item.title}»</b> успешно размещено.\n\n"
                "Теперь его могут видеть другие пользователи в поиске. "
                "Когда кто-то захочет арендовать вашу вещь — вы получите уведомление.",
                #reply_markup=get_item_confirmation_keyboard(),
                parse_mode="HTML"
            )

            # 4️⃣ очищаем FSM
            await state.clear()  # очищаем FSM

            # 5️⃣ ведём в главное меню
            #from handlers.base import show_main_menu
            #return await show_main_menu(callback.message, state)

        except Exception as e:
            logger.error(f"[FSM] Ошибка при создании объявления: {e}", exc_info=True)
            await callback.message.answer(
                "❌ Произошла ошибка при создании объявления. Попробуйте позже.",
                #reply_markup=get_item_confirmation_keyboard()
            )
            #from handlers.base import show_main_menu
            #return await show_main_menu(callback.message, state)

    # 2. редактирование (думаю это тут лишнее)
    elif action == "edit_item":
         await callback.message.edit_text(
            "📝 <b>Редактирование объявления</b>\n\n"
            "Выберите, что вы хотите изменить:",
            parse_mode="HTML"
        )
        # тут потом можно вызывать show_edit_item_menu(callback, state)
        #return

    # ❌ 3. ОТМЕНА
    else:
        await callback.message.answer(
            "❌ Создание объявления отменено.",
            #reply_markup=get_item_confirmation_keyboard()
        )
        await state.clear() # ❌ Удаляет всё: и состояние, и данные

        # await state.set_state(None) # 🔄 Сбрасывает|очистить состояние, но сохраняет данные
        # FSM “выйдет” из состояния, но state_data (например, new_item) сохранится

        # await state.update_data(new_item={})  # сбросить только объявление      # ✏️ Изменяет/очищает часть данных

        #from handlers.base import show_main_menu
        #return await show_main_menu(callback.message, state)


@items_router.callback_query(F.data.startswith("edit_item:"))
async def start_process_edit_item(callback: CallbackQuery, state: FSMContext, item_service: ItemService):
    """📝 Начало процесса редактирования объявления"""
    await callback.answer()

    # Получаем item_id из callback_data
    try:
        item_id = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        await callback.message.answer("❌ Ошибка: некорректный ID объявления.")
        return

    # Получаем объявление
    item = await item_service.get_item_by_id(item_id)
    if not item:
        await callback.message.answer("❌ Объявление не найдено.")
        return

    # Сохраняем данные для редактирования
    await state.update_data(edit_item_id=item_id)

    # Клавиатура редактирования
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Название", callback_data="edit_field:title")],
        [InlineKeyboardButton(text="📋 Описание", callback_data="edit_field:description")],
        [InlineKeyboardButton(text="💰 Цена", callback_data="edit_field:price")],
        [InlineKeyboardButton(text="🔐 Залог", callback_data="edit_field:deposit")],
        [InlineKeyboardButton(text="📍 Местоположение", callback_data="edit_field:location")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data=f"show_item:{item_id}")]
    ])

    await callback.message.edit_text(
        f"✏️ <b>Редактирование объявления</b>\n\n"
        f"Выберите, что вы хотите изменить в <b>«{item.title}»</b>:",
        parse_mode="HTML",
        reply_markup=keyboard
    )

#=======================================мини-функции================================================
def get_items_count_str(count: int) -> str:
    """Возвращает правильное склонение слова 'объявление'"""
    if count % 10 == 1 and count % 100 != 11:
        return "объявление"
    elif 2 <= count % 10 <= 4 and (count % 100 < 10 or count % 100 >= 20):
        return "объявления"
    else:
        return "объявлений"

def get_days_str(days: int) -> str:
    """Возвращает правильное склонение слова 'день'"""
    if days % 10 == 1 and days % 100 != 11:
        return "день"
    elif 2 <= days % 10 <= 4 and (days % 100 < 10 or days % 100 >= 20):
        return "дня"
    else:
        return "дней"


#======================================Изменение объявления====================================================
