import logging
from aiogram import F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
from decimal import Decimal, InvalidOperation

from .router import items_router

from services.item_service import ItemService
from services.photo_service import PhotoService
from services.category_service import CategoryService
from schemas.item import ItemCreateDraft, ItemCreate
from states.item import ItemCreateStates
from keyboards.category_kb import build_category_keyboard
from keyboards.item_kb import get_photos_keyboard, build_edit_item_keyboard, cancel_keyboard
from utils.functions import send_or_edit, format_step
from utils.errors import ServiceError, ValidationError

logger = logging.getLogger(__name__)

CAT_FI_PREFIX = "cat_for_item:"
SUBCAT_FI_PREFIX = "subcat_for_item:"

BACK_TO_MENU_CB = "back_to_main_menu" # "back_to_menu"

BACK_TO_CAT = "back_to_categories"
ADD_ITEM_CB = "add_item"

PUBLISH_ITEM_CB = "publish_item:"
EDIT_ITEM_CB = "edit_item:"
CANCEL_ITEM_CB = "cancel_item:"

MAX_PHOTOS = 5

"""
Начинает процесс создания объявления (оба сценария: с категорией и без неё)

Сценарий 1 (главное меню «📦 Сдать в аренду»): event = Message             (вызов в base.py)
    — категории ещё нет → сразу просим название и ставим FSM на title.
    (категория/подкатегория пока неизвестны → просто создаём болванку и просим название)

Сценарий 2 (после выбора подкатегории): event = CallbackQuery с data вида "subcat:<id>"
    — извлекаем subcategory_id, берём category по parent_id, сохраняем в FSM и просим название.

    «➕ Добавить объявление» (inline-кнопка внутри списка «Мои объявления»)
"""
# ============================== СЦЕНАРИЙ 2 (Callback)  =================================
@items_router.callback_query(F.data == ADD_ITEM_CB)
async def start_create_item_from_my_items(
        callback: CallbackQuery,
        state: FSMContext,
        category_service: CategoryService,
        user
) -> None:
    """Запуск процесса создания объявления из списка 'Мои объявления'.
    Создаёт новый контекст FSM, подготавливает new_item и показывает категории."""

    await callback.answer()

    """    
    data = await state.get_data()
    selected_category_id = data.get("selected_category_id")
    selected_category_name = data.get("selected_category_name")
    selected_subcategory_id = data.get("selected_subcategory_id")
    selected_subcategory_name = data.get("selected_subcategory_name")
    selected_item_id = data.get("selected_item_id")

    # 🔄 Очистим все предыдущие данные
    await state.clear()

    await state.update_data(
        selected_category_id=selected_category_id,
        selected_category_name=selected_category_name,
        selected_subcategory_id=selected_subcategory_id,
        selected_subcategory_name=selected_subcategory_name,
        selected_item_id=selected_item_id
    )
    """

    # 🔄 Очистим все предыдущие данные
    await state.clear() # data сейчас: пусто

    draft = ItemCreateDraft() # category_id/title/price ещё None, а дефолтные поля будут заполнены БД

    # 💾 Инициализация FSM
    await state.update_data( # данные которые можно заполнить сразу
        mode="create_item",
        user_id=user.id,
        new_item=draft.model_dump(), # пока пусто, начнем заполнять
    )

    # Переводим FSM в первое состояние - выбор категории
    await state.set_state(ItemCreateStates.category)

    # ⚙️ Получаем категории
    try:
        categories = await category_service.list_main_categories()
    except ServiceError:
        await send_or_edit(callback, "⚠️ Не удалось загрузить категории. Попробуйте позже.")
        return

    categories = categories or []

    # 🧱 Формируем клавиатуру
    keyboard = build_category_keyboard(
        categories,
        prefix=CAT_FI_PREFIX,
        extra_buttons=[[InlineKeyboardButton(text="🔙 Назад в меню", callback_data=BACK_TO_MENU_CB)]]
    )

    message_text = "📦 <b>Сдать в аренду</b>\n\nВыберите категорию для вашего объявления:"

    await send_or_edit(callback, message_text, markup=keyboard)
    # data сейчас: mode, new_item, user (id)


@items_router.callback_query(F.data.startswith(CAT_FI_PREFIX))
async def show_subcategories_for_creating_item(callback: CallbackQuery, state: FSMContext, category_service: CategoryService) -> None:
    """Показывает подкатегории для FSM-сценария 'Создать объявление'."""

    await callback.answer()

    try:
        category_id = int(callback.data.split(":")[1]) # .split(":", 1)
    except (IndexError, ValueError):
        await send_or_edit(callback, "⚠️ Не удалось распознать категорию.")
        return

    try:
        category = await category_service.get_category(category_id)
        subcategories = await category_service.list_subcategories(category_id)
    except ServiceError:
        await send_or_edit(callback, "⚠️ Не удалось загрузить категории. Попробуйте позже.")
        return

    if not category:
        # await callback.answer("⚠️ Категория не найдена", show_alert=True)
        await send_or_edit(callback, "⚠️ Категория не найдена")
        return

    subcategories = subcategories or []
    if not subcategories:
        text = f"⚠️ В категории <b>{category.name}</b> пока нет подкатегорий."
        await send_or_edit(callback, text)
        return

    await state.update_data(
        selected_category_id=category.id,
        selected_category_name=category.name,
        # при смене категории логично сбросить подкатегорию
        selected_subcategory_id=None,
        selected_subcategory_name=None,
    )

    keyboard = build_category_keyboard(
        subcategories,
        prefix=SUBCAT_FI_PREFIX,
        extra_buttons=[[InlineKeyboardButton(text="🔙 Назад (к категориям)", callback_data=BACK_TO_CAT)]] # "create_back_to_cat"
    )

    text = (
        f"📦 <b>Выбор категории для объявления</b>\n\n"
        f"Выбрана категория: <b>{category.name}</b>\n"
        f"Уточните подкатегорию:"
    )

    await send_or_edit(callback, text, markup=keyboard)
    # data сейчас: mode, new_item, id (user, category), name (category)

    # FSM пока остаётся в состоянии category: переход произойдёт позже — при выборе конкретной подкатегории


@items_router.callback_query(F.data.startswith(SUBCAT_FI_PREFIX))
async def start_create_item_from_subcategory(callback: CallbackQuery, state: FSMContext, category_service: CategoryService) -> None:
    """Переход из подкатегории к вводу названия вещи."""

    await callback.answer()

    try:
        subcategory_id = int(callback.data.split(":")[1]) # .split(":", 1)
    except (IndexError, ValueError):
        await send_or_edit(callback, "⚠️ Не удалось распознать подкатегорию.")
        return

    try:
        subcategory = await category_service.get_category(subcategory_id)
    except ServiceError:
        await send_or_edit(callback, "⚠️ Не удалось загрузить подкатегорию. Попробуйте позже.")
        return

    if not subcategory:
        await send_or_edit(callback, "⚠️ Подкатегория не найдена")
        return # show_categories()

    # пробуем достать категорию из state
    data = await state.get_data()
    category_id = data.get("selected_category_id")

    if not category_id: # пробуем получить категория из подкатегории
        category_id = getattr(subcategory, "parent_id", None)

    try:
        category = await category_service.get_category(category_id)
    except ServiceError:
        await send_or_edit(callback, "⚠️ Не удалось загрузить категорию. Попробуйте позже.")
        return

    if not category:
        await callback.answer("⚠️ Категория не найдена", show_alert=True)
        return # show_categories()

    # Валидируем черновик из FSM (FSM все_равно хранит dict)
    draft = ItemCreateDraft.model_validate(data.get("new_item") or {})

    # обновляем FSM данными
    draft.category_id = category_id
    draft.subcategory_id = subcategory.id

    """ Было  
    #new_item = data.get("new_item", {})
    new_item = dict(data.get("new_item") or {}) # лучше сделать копию, надежней - GPT

    new_item["category_id"] = category_id
    new_item["subcategory_id"] = subcategory.id
    """

    await state.update_data(
        selected_category_id=category_id,
        selected_category_name=category.name,
        selected_subcategory_id=subcategory.id,
        selected_subcategory_name=subcategory.name,
        new_item=draft.model_dump()
    )

    # уходим в общую для двух сценариев функцию
    await start_create_item_title(callback, state, category, subcategory)
    # data сейчас: mode, new_item_1, id (user | category | subcat), name (category|subcat)

# ========================== СЦЕНАРИЙ 1 (Message) =======================================
async def start_create_item_from_menu(message: Message, state: FSMContext, user) -> None:
    """Сценарий 1: старт создания объявления из меню без выбора категории/подкатегории"""

    await state.clear()

    draft = ItemCreateDraft()

    draft.category_id = 999 # 🔹 временная заглушка
    draft.subcategory_id = 999 # 🔹 временная заглушка

    await state.update_data(
        mode="create_item",
        user_id=user.id,
        new_item=draft.model_dump(),
    )

    # уходим в общую для двух сценариев функцию
    await start_create_item_title(message, state)

    # data сейчас: mode, new_item_1, id (user | category | subcat), name (category|subcat)

# =========================== Начинается FSM для обоих сценариев =========================
async def start_create_item_title(event: Message | CallbackQuery, state: FSMContext, category=None, subcategory=None) -> None:
    """Показывает пользователю приглашение ввести название вещи."""

    logger.info(f"[FSM] → Старт создания объявления ({'из меню.' if category is None else 'из подкатегории.'})")

    cat_text = f"Категория: <b>{category.name}</b>\n" if category else ""
    subcat_text = f"Подкатегория: <b>{subcategory.name}</b>\n" if subcategory else ""
    text = (
        "📦 <b>Ваше новое объявление</b>\n\n"
        f"{cat_text}{subcat_text}\n"
        "📝 Введите название вещи:"
    )

    # переводим FSM в состояние ожидания названия
    await state.set_state(ItemCreateStates.title)
    # logger.debug(f"[FSM] Установлено состояние: {await state.get_state()}")

    await send_or_edit(event, text, markup=cancel_keyboard()) # get_back_inline_keyboard()


@items_router.message(ItemCreateStates.title)
async def process_item_title(message: Message, state: FSMContext) -> None:
    """Обрабатывает ввод названия при создании объявления"""

    title = (message.text or "").strip()

    error_msg: str | None = None
    if not title:
        error_msg = "❌ Название не должно быть пустым. Введите название вещи."
    elif len(title) < 3:
        error_msg = "❌ Название слишком короткое. Введите не менее 3 символов."
    elif len(title) > 255:
        error_msg = "❌ Название слишком длинное. Введите не более 255 символов."

    if error_msg:
        await message.answer(
            format_step(error_msg, 1, 6),
            reply_markup=cancel_keyboard(), # get_back_inline_keyboard()
            parse_mode="HTML",
        )
        return # остаёмся в том же состоянии (title)

    # сохраняем во временное хранилище FSM
    data = await state.get_data()
    draft = ItemCreateDraft.model_validate(data.get("new_item") or {})
    draft.title = title
    await state.update_data(new_item=draft.model_dump())
    # logger.info("[FSM] Название сохранено: %s", title)

    description = ("📋 *Описание объявления* ✍️\n\n"
                   "Пожалуйста, введите подробное описание вещи. Укажите:\n"
                   "- Состояние и особенности\n"
                   "- Комплектацию\n"
                   "- Особенности использования\n"
                   "- Другую важную информацию")

    # переводим FSM в следующее состояние
    await state.set_state(ItemCreateStates.description)
    # data сейчас: mode, new_item (title), id (user | category | subcat), name (category|subcat)

    await message.answer(
        format_step(description ,2, 6),
        parse_mode="HTML",
        reply_markup=cancel_keyboard() # get_back_inline_keyboard("back_to_item_title")
    )


@items_router.message(ItemCreateStates.description)
async def process_item_description(message: Message, state: FSMContext) -> None:
    """Обрабатывает ввод описания объявления"""

    description = (message.text or "").strip()

    error_msg: str | None = None
    if not description:
        error_msg = "❌ Описание не должно быть пустым. Введите описание вещи."
    elif len(description) < 10:
        error_msg = "❌ Описание слишком короткое. Пожалуйста, введите более подробное описание (минимум 10 символов)"

    if error_msg:
        await message.answer(
            format_step(error_msg, 2, 6),
            reply_markup=cancel_keyboard(),  # get_back_inline_keyboard("back_to_item_title")
            parse_mode="HTML",
        )
        return  # остаёмся в том же состоянии (description)

    # Сохраняем описание в FSM
    data = await state.get_data()
    draft = ItemCreateDraft.model_validate(data.get("new_item") or {})
    draft.description = description
    await state.update_data(new_item=draft.model_dump())
    # logger.info("[FSM] Описание сохранено: %s...", description[:40])

    # Переход к следующему шагу
    await state.set_state(ItemCreateStates.price)

    price_mes = ("💰 *Цена аренды*\n\n"
                 "Укажите стоимость аренды за один день (только число).\n"
                 "Например: 500")
    # "Укажите стоимость аренды в формате '500 руб/день' или '100 руб/час':"

    await message.answer(
        format_step(price_mes ,3, 6),
        parse_mode="HTML",
        reply_markup= cancel_keyboard() # get_back_inline_keyboard("back_to_item_description")
    )


@items_router.message(ItemCreateStates.price)
async def process_item_price(message: Message, state: FSMContext) -> None:
    """Обрабатывает ввод цены аренды (шаг FSM)"""

    price_text = (message.text or "").strip().replace(",", ".") # Преобразуем введённое значение в число

    try:
        price = Decimal(price_text)
    except (InvalidOperation, ValueError):
        await message.answer(
            format_step("❌ Некорректное значение.\nВведите цену — только число, больше 0.",
                        3, 6),
            reply_markup=cancel_keyboard(), # get_back_inline_keyboard("back_to_item_description"),
        )
        return  # остаёмся в том же состоянии (price)

    if price <= 0:
        text = format_step("❌ Цена должна быть положительным числом." ,3, 6)
        await message.answer(text, reply_markup=cancel_keyboard(), parse_mode="HTML")
        return  # остаёмся в том же состоянии (price)

    # Сохраняем цену в FSM
    data = await state.get_data()

    draft = ItemCreateDraft.model_validate(data.get("new_item") or {})
    draft.price = price
    await state.update_data(new_item=draft.model_dump())
    # logger.info(f"[FSM] Цена аренды сохранена: {price}")

    # Переходим к следующему шагу FSM — залог
    await state.set_state(ItemCreateStates.deposit)

    # ✅ Следующий шаг: залог
    deposit_mes = ("🔐 *Залог*\n\n"
                   "Укажите сумму залога (только число).\n"
                   "💡 Залог возвращается после возврата вещи в исходном состоянии.\n"
                   "Например: 5000")

    await message.answer(
        format_step(deposit_mes ,4, 6),
        parse_mode="HTML",
        reply_markup=cancel_keyboard() # get_back_inline_keyboard("back_to_item_description")
    )


@items_router.message(ItemCreateStates.deposit)
async def process_item_deposit(message: Message, state: FSMContext) -> None:
    """Обрабатывает ввод суммы залога (шаг FSM)."""

    deposit_text = (message.text or "").strip().replace(",", ".") # Преобразуем введённое значение в число

    try:
        deposit = Decimal(deposit_text)
    except (InvalidOperation, ValueError):
        text = format_step("❌ Некорректное значение. Пожалуйста, введите число." ,4, 6)
        await message.answer(text ,reply_markup= cancel_keyboard()
                             ,parse_mode="HTML")  # get_back_inline_keyboard("back_to_item_price"),
        return  # остаёмся в состоянии deposit

    if deposit < 0:
        text = format_step("❌ Сумма залога не может быть отрицательной." ,4, 6)
        await message.answer(text, reply_markup=cancel_keyboard(), parse_mode="HTML") # get_back_inline_keyboard("back_to_item_price")
        return  # остаёмся в состоянии deposit

    # Сохраняем сумму залога в FSM
    data = await state.get_data()
    draft = ItemCreateDraft.model_validate(data.get("new_item") or {})
    draft.deposit = deposit
    await state.update_data(new_item=draft.model_dump())
    # logger.info(f"[FSM] Сумма залога сохранена: {deposit}")

    await state.set_state(ItemCreateStates.location)

    # Переходим к следующему шагу FSM (местоположение)
    place_mes = ("📍 *Местоположение*\n\n"
                 "Укажите, где находится вещь (город, район, метро и т.д.).\n"
                 "Эта информация будет видна потенциальным арендаторам.")

    await message.answer(format_step(place_mes ,5, 6), parse_mode="HTML", reply_markup=cancel_keyboard()) # get_back_inline_keyboard("back_to_item_description")


@items_router.message(ItemCreateStates.location)
async def process_item_location(message: Message, state: FSMContext) -> None:
    """Обрабатывает ввод местоположения вещи (шаг FSM)."""

    location = (message.text or "").strip()

    if len(location) < 3:
        text = format_step("❌ Местоположение слишком короткое. Пожалуйста, укажите хотя бы город/район." ,5, 6)
        await message.answer(text ,reply_markup=cancel_keyboard()
                             ,parse_mode="HTML") # get_back_inline_keyboard("back_to_item_deposit")
        return  # остаёмся в состоянии location

    # Сохраняем местоположение в FSM
    data = await state.get_data()
    draft = ItemCreateDraft.model_validate(data.get("new_item") or {})
    draft.location = location
    await state.update_data(new_item=draft.model_dump())
    # logger.info(f"[FSM] Местоположение сохранено: {location}")

    # Переходим к следующему шагу FSM — минимальный срок аренды
    await state.set_state(ItemCreateStates.rental_period)

    min_period_mes = ("⏱️ <b>Отлично!</b>\n\n"
                      "Теперь укажите <b>минимальный срок аренды</b>.\n"
                      "Например: <code>1 день</code>, <code>3 часа</code>, <code>2 недели</code>.")

    await message.answer(format_step(min_period_mes ,6, 6), parse_mode="HTML", reply_markup=cancel_keyboard()) # get_back_inline_keyboard("back_to_item_location")


@items_router.message(ItemCreateStates.rental_period)
async def process_item_rental_period(message: Message, state: FSMContext) -> None:
    """Обрабатывает ввод минимального срока аренды и показывает итоговое подтверждение объявления"""

    rental_period = (message.text or "").strip()

    try:
        min_days = int(rental_period)
    except ValueError:
        await message.answer(
            format_step("❌ Некорректное значение. Введите число дней, например: <code>1</code>.", 6, 6),
            reply_markup=cancel_keyboard(),
            parse_mode="HTML",
        )
        return

    if min_days < 1:
        await message.answer(
            format_step("❌ Минимальный срок аренды должен быть не меньше 1 дня.", 6, 6),
            reply_markup=cancel_keyboard(), # get_back_inline_keyboard("back_to_item_location")
            parse_mode="HTML",
        )
        return # остаёмся в состоянии rental_period

    # Сохраняем срок в FSM
    data = await state.get_data()
    draft = ItemCreateDraft.model_validate(data.get("new_item") or {})
    draft.min_rental_period = min_days
    await state.update_data(new_item=draft.model_dump())
    # logger.info(f"[FSM] Минимальный срок аренды сохранён: {rental_period}")

    # Переход к шагу загрузки фото
    await state.set_state(ItemCreateStates.photos)

    text = ("📸 Теперь загрузите фотографии вещи.\n"
            "Можно загрузить до 5 штук.\n"
            "Когда закончите — нажмите <b>«Готово»</b>.")

    await message.answer(text, reply_markup=get_photos_keyboard(), parse_mode="HTML")

# -------------- ЛОГИКА ДОБАВЛЕНИЯ ФОТОГРАФИЙ ------------
# убираем эту кнопку
# @items_router.message(ItemCreateStates.photos, F.text == "🔙 Назад")
# async def photos_back(message: Message, state: FSMContext):
#     """Возврат к предыдущему шагу (например, к описанию)."""
#     await message.answer("Возвращаемся назад. Введите описание товара:",
#                          reply_markup= get_back_inline_keyboard("back_to_item_rental_period")) # ???
#     await state.set_state(ItemCreateStates.description)

@items_router.message(ItemCreateStates.photos, F.text == "✅ Готово")
async def photos_done(message: Message, state: FSMContext):
    """Пользователь завершил загрузку фотографий."""

    data = await state.get_data()
    photos = data.get("photos", []) # держим отдельно от ItemCreateDraft

    if not photos:
        await message.answer(
            "⚠️ Вы не загрузили ни одной фотографии.\n"
            "Вы можете продолжить, но объявление будет без фото.",
        )

    # Переходим к финальному подтверждению
    await state.set_state(ItemCreateStates.confirmation)

    await show_item_confirmation(message, state)


@items_router.message(ItemCreateStates.photos, F.photo)
async def process_item_photos(message: Message, state: FSMContext) -> None:
    """Обработка загруженной фотографии. Тут собираем все фото пользователя"""

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
    await state.update_data(photos=photos) # держим отдельно от ItemCreateDraft

    await message.answer(
        f"📸 Фото загружено! ({len(photos)}/{MAX_PHOTOS})\n"
        "Отправьте ещё фото (вы можете загрузить еще {5 - len(photos)})"
        "или нажмите «✅ Готово».",
        reply_markup=get_photos_keyboard()
    )

@items_router.message(ItemCreateStates.photos)
async def photos_wrong_input(message: Message):
    """Обработка неверного ввода (не фото и не команда)."""
    await message.answer(
        "❌ Пожалуйста, отправьте фотографию.\n"
        "Или нажмите «Готово».",
        reply_markup=get_photos_keyboard(), # ✅ Готово / 🔙 Назад   (reply keyboard)
    )
# ----------------------------------------------------

async def show_item_confirmation(message: Message, state: FSMContext) -> None:
    """Показывает итоговое подтверждение объявления."""

    data = await state.get_data()
    draft = ItemCreateDraft.model_validate(data.get("new_item") or {})

    title = draft.title or "Без названия"
    description = draft.description or "Нет описания"
    description_short = description[:120] + ("..." if len(description) > 120 else "")
    # = description[:120]}{'...' if len(description) > 120 else ''

    price = draft.price if draft.price is not None else Decimal("0")
    deposit = draft.deposit if draft.deposit is not None else Decimal("0")

    location = draft.location or "Не указано"
    min_period = draft.min_rental_period

    photos: list[str] = data.get("photos") or []

    confirmation_text = (
        f"📦 <b>Подтверждение объявления</b>\n\n"
        f"📝 <b>Название:</b> {title}\n"
        f"📋 <b>Описание:</b> {description_short}\n"
        f"💰 <b>Цена:</b> {price} ₽/день\n"
        f"🔐 <b>Залог:</b> {deposit} ₽\n"
        f"📍 <b>Местоположение:</b> {location}\n"
        f"⏱️ <b>Мин. срок аренды:</b> {min_period}\n"
        f"📸 <b>Фотографий:</b> {len(photos)}\n\n"
        f"Всё верно? Подтвердите создание объявления 👇"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Разместить объявление", callback_data=PUBLISH_ITEM_CB)],
            [InlineKeyboardButton(text="❌ Удалить объявление", callback_data=CANCEL_ITEM_CB)], # BACK_TO_MENU_CB
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
        except TelegramBadRequest:
            # если caption/фото не прошло — покажем текстом
            pass

    await message.answer(confirmation_text ,reply_markup=keyboard ,parse_mode="HTML")

# ======================================= финальные обработки ================================================

# Обработка подтверждения ✅ публикации объявления
@items_router.callback_query(F.data.startswith(PUBLISH_ITEM_CB))
async def process_item_confirmation(
        callback: CallbackQuery,
        state: FSMContext,
        item_service: ItemService,
        photo_service: PhotoService,
        user
) -> None:
    """Обрабатывает подтверждение создания объявления - ПУБЛИКАЦИЯ ОБЪЯВЛЕНИЯ"""

    await callback.answer()

    data = await state.get_data()
    new_item = data.get("new_item") or {}
    photos: list[str] = data.get("photos") or [] # data.get("photos", [])

    if not new_item:
        await send_or_edit(callback, "❌ Данные объявления не найдены. Начните создание заново.")
        return

    # Валидация Draft
    try:
        draft = ItemCreateDraft.model_validate(new_item)
    except ValidationError:
        await send_or_edit(callback, "❌ Данные объявления повреждены. Начните создание заново.")
        # ❌ Произошла ошибка при создании объявления. Попробуйте позже.
        return

    # Финальная валидация Create-схемы (строгий контракт)
    try:
        payload = ItemCreate.model_validate(draft.model_dump())
    except ValidationError:
        # Можно сделать красивый разбор ошибок, но для MVP — коротко
        await send_or_edit(
            callback,
            "❌ Объявление заполнено не полностью или содержит ошибки.\n"
            "Проверьте поля и попробуйте снова.",
        )
        return

    # Создание объявления (доменная логика внутри сервиса!)
    try:
        # new_item["status"] = "PENDING"  # NEW (Admin logic) - дефолт устанавливает Модель/БД
        created_item = await item_service.create(user_id=user.id, item_data=payload)
    except ServiceError:
        await send_or_edit(callback, "❌ Не удалось создать объявление. Попробуйте позже.")
        return

    # сохраняем фотографии отдельно
    item_id = created_item.id
    if photos:
        try:
            await photo_service.add_photos(item_id, photos)
            # logger.info(f"[FSM] Сохранено {len(photos)} фото для item_id={item_id}")
        except ServiceError:
            # На MVP: просто предупреждаем пользователя и идём дальше
            await callback.message.answer(
                "⚠️ Объявление создано, но фото не удалось сохранить. Попробуйте добавить их позже.",
                parse_mode="HTML",
            )

    # сообщение пользователю
    text = (f"✅ <b>Поздравляем!</b>\n\n"
            f"Ваше объявление <b>«{created_item.title}»</b> успешно создано.\n\n"
            "Сейчас объявление отправлено на модерацию, появится после одобрения, и "
            "и его увидят другие пользователи в поиске. "
            "Когда кто-то захочет арендовать вашу вещь — вы получите уведомление.")

    await callback.message.answer(
        text,
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove(),  # убираем reply-клаву фото
    )

    # очищаем FSM
    await state.clear()

    # 5️⃣ ведём в главное меню ???
    # await show_main_menu(callback.message, state)

#  Обработка отмены ❌
@items_router.callback_query(F.data.startswith(CANCEL_ITEM_CB))
@items_router.callback_query(F.data == BACK_TO_MENU_CB)
async def cancel_flow_to_main_menu(callback: CallbackQuery,  state: FSMContext) -> None:
    """❌ Отмена: полностью выходим из FSM, убираем reply-клавиатуру и возвращаем в главное меню."""

    await callback.answer()

    # 1) ❌ Полностью очищаем FSM (состояние + данные)
    await state.clear()

    # await state.set_state(None) # 🔄 Сбрасывает|очищает состояние, но сохраняет данные. FSM “выйдет” из состояния,
    # но state_data (например, new_item) сохранится

    # await state.update_data(new_item={})  # сбросить только объявление # ✏️ Изменяет/очищает часть данных

    # 2) Убираем reply-клавиатуру (после фото-шагов)
    await callback.message.answer(
        "❌ Создание объявления отменено.",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="HTML",
    )

    # 3) Главное меню
    # await show_main_menu(callback.message, state)


# Обработка редактирования ✏️ (логика не завершена)
@items_router.callback_query(F.data.startswith(EDIT_ITEM_CB))
async def start_process_edit_item(callback: CallbackQuery, state: FSMContext, item_service: ItemService) -> None:
    """📝 Начало процесса редактирования объявления"""

    await callback.answer()

    try:
        item_id = int(callback.data.split(":")[1]) # .split(":", 1)
    except (IndexError, ValueError):
        await send_or_edit(callback, "❌ Ошибка: некорректный ID объявления.")
        return

    try:
        item = await item_service.get_item_by_id(item_id)
    except ServiceError:
        await send_or_edit(callback, "❌ Не удалось загрузить объявление. Попробуйте позже.")
        return

    if not item:
        await send_or_edit(callback, "❌ Объявление не найдено.")
        return

    # Сохраняем данные для редактирования
    await state.update_data(
        edit_item_id=item_id,
        edit_field=None,
    )

    # Клавиатура редактирования
    keyboard = build_edit_item_keyboard(item_id)

    safe_title = item.title or "Без названия"
    text = (f"✏️ <b>Редактирование объявления</b>\n\n"
            f"Выберите, что вы хотите изменить в <b>«{safe_title}»</b>:",)

    await send_or_edit(callback, text, markup=keyboard, parse_mode="HTML")
# ====================================== Редактирования ✏️ объявления ==================================================