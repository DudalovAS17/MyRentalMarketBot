import logging
from aiogram import F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext

from .router import items_router

from handlers.item import create_helpers as ch
from handlers.entries.base_entry import show_main_menu
from services.item_service import ItemService
from services.photo_service import PhotoService
from services.category_service import CategoryService
from schemas.item import ItemCreateDraft, ItemCreate
from states.item import ItemCreateStates
from keyboards.item_kb import get_photos_keyboard, build_edit_item_keyboard, cancel_keyboard
from utils.functions import send_or_edit
from utils.errors import ServiceError, ValidationError
from utils.validators import parse_callback
from utils.callbacks import (CAT_FI_PREFIX, SUBCAT_FI_PREFIX, ADD_ITEM_CB, PUBLISH_ITEM_CB, EDIT_ITEM_CB,
                             CANCEL_ITEM_CB, MAX_PHOTOS, CREATE_ITEM_MODE) #, BACK_TO_MENU_CB, BACK_TO_CAT

logger = logging.getLogger(__name__)

"""
Начинает процесс создания объявления (оба сценария: с категорией и без неё)

Сценарий 1 (главное меню «📦 Сдать в аренду»): event = Message             (вызов в base.py)
    — категории ещё нет → сразу просим название и ставим FSM на title.
    (категория/подкатегория пока неизвестны → просто создаём болванку и просим название)

Сценарий 2 (после выбора подкатегории): event = CallbackQuery с data вида "subcat:<id>"
    — извлекаем subcategory_id, берём category по parent_id, сохраняем в FSM и просим название.

    «➕ Добавить объявление» (inline-кнопка внутри списка «Мои объявления»)
"""

# ─────────────────────────────────────────────── СЦЕНАРИЙ 2 (Callback) ────────────────────────────────────────────────
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

    # 🔄 Очистим все предыдущие данные (data сейчас: пусто)
    await state.clear()

    draft = ItemCreateDraft() # category_id/title/price ещё None, а дефолтные поля будут заполнены БД

    # 💾 Инициализация FSM
    await state.update_data( # данные которые можно заполнить сразу
        mode=CREATE_ITEM_MODE,
        user_id=user.id,
        new_item=draft.model_dump(), # пока пусто, начнем заполнять
    )

    # Переводим FSM в первое состояние - выбор категории
    await state.set_state(ItemCreateStates.category)

    # ⚙️ Получаем категории
    await ch.show_create_item_categories_step(callback, category_service)

    # data сейчас: mode, new_item, user (id)


@items_router.callback_query(F.data.startswith(CAT_FI_PREFIX))
async def show_subcategories_for_creating_item(callback: CallbackQuery, state: FSMContext, category_service: CategoryService) -> None:
    """Показывает подкатегории для FSM-сценария 'Создать объявление'."""
    await callback.answer()

    category = await ch.load_entity_or_notify(callback, category_service.get_category_by_id,
                                              parse_callback(callback.data, CAT_FI_PREFIX),
                                              invalid_id_text=ch.not_cat_id, load_error_text=ch.serv_err_cat,
                                              not_found_text=ch.not_cat)

    not_subcats = f"⚠️ В категории <b>{category.name}</b> пока нет подкатегорий."
    subcategories = await ch.load_entity_or_notify(callback, category_service.list_subcategories, category.id,
                                                 invalid_id_text=ch.not_cat_id, load_error_text=ch.serv_err_cat,
                                                 not_found_text=not_subcats)

    await ch.store_selected_category(state, category)

    subcategories = subcategories or []
    await send_or_edit(callback, ch.create_item_subcategory_step_text(category.name), markup=ch.build_create_item_subcategories_keyboard(subcategories))

    # 1) data сейчас: mode, new_item, id (user, category), name (category)
    # 2) FSM пока остаётся в состоянии category: переход произойдёт позже — при выборе конкретной подкатегории


@items_router.callback_query(F.data.startswith(SUBCAT_FI_PREFIX))
async def start_create_item_from_subcategory(callback: CallbackQuery, state: FSMContext, category_service: CategoryService) -> None:
    """Переход из подкатегории к вводу названия вещи."""
    await callback.answer()

    subcategory = await ch.load_entity_or_notify(callback, category_service.get_category_by_id,
                                                 parse_callback(callback.data, SUBCAT_FI_PREFIX),
                                                 invalid_id_text=ch.not_subcat_id, load_error_text=ch.serv_err_subcat,
                                                 not_found_text=ch.not_subcat)

    # пробуем достать категорию из state
    data = await state.get_data()
    category_id = data.get("selected_category_id")

    if not category_id: # пробуем получить категория из подкатегории
        category_id = getattr(subcategory, "parent_id", None)

    category = await ch.load_entity_or_notify(callback, category_service.get_category_by_id, category_id,
                                              invalid_id_text=ch.not_cat_id, load_error_text=ch.serv_err_cat,
                                              not_found_text=ch.not_cat)

    # Валидируем черновик из FSM (FSM все_равно хранит dict)
    draft = ItemCreateDraft.model_validate(data.get("new_item") or {})

    # обновляем FSM данными
    draft.category_id = category_id
    draft.subcategory_id = subcategory.id

    await ch.store_selected_subcategory(state=state, category=category, subcategory=subcategory, draft=draft)

    # уходим в общую для двух сценариев функцию
    await start_create_item_title(callback, state, category, subcategory)
    # data сейчас: mode, new_item_1, id (user | category | subcat), name (category|subcat)

# ─────────────────────────────────────────────── СЦЕНАРИЙ 1 (Message) ─────────────────────────────────────────────────
async def start_create_item_from_menu(message: Message, state: FSMContext, user) -> None:
    """Сценарий 1: старт создания объявления из меню без выбора категории/подкатегории"""

    await state.clear()

    draft = ItemCreateDraft()
    draft.category_id = 999 # 🔹 временная заглушка
    draft.subcategory_id = 999 # 🔹 временная заглушка

    await state.update_data(
        mode=CREATE_ITEM_MODE,
        user_id=user.id,
        new_item=draft.model_dump(),
    )

    # уходим в общую для двух сценариев функцию
    await start_create_item_title(message, state)

    # data сейчас: mode, new_item_1, id (user | category | subcat), name (category|subcat)

# ───────────────────────────────────────── Начинается FSM для обоих сценариев ─────────────────────────────────────────
async def start_create_item_title(event: Message | CallbackQuery, state: FSMContext, category=None, subcategory=None) -> None:
    """Показывает пользователю приглашение ввести название вещи."""
    #logger.info(f"[FSM] → Старт создания объявления ({'из меню.' if category is None else 'из подкатегории.'})")

    # переводим FSM в состояние ожидания названия
    await state.set_state(ItemCreateStates.title)

    await send_or_edit(event, ch.create_new_item_text(category, subcategory), markup=cancel_keyboard()) # get_back_inline_keyboard()


@items_router.message(ItemCreateStates.title)
async def process_item_title(message: Message, state: FSMContext) -> None:
    """Обрабатывает ввод названия при создании объявления"""

    title = ch.extract_item_text_input(message)
    error_msg = ch.validate_item_title(title)

    if error_msg:
        await ch.render_create_item_step_message(message, error_msg, 1, 6)  # get_back_inline_keyboard()
        return # остаёмся в том же состоянии (title)

    # сохраняем во временное хранилище FSM
    data = await state.get_data()
    draft = ItemCreateDraft.model_validate(data.get("new_item") or {})
    draft.title = title
    await state.update_data(new_item=draft.model_dump())

    # переводим FSM в следующее состояние
    await state.set_state(ItemCreateStates.description)
    # data сейчас: mode, new_item (title), id (user | category | subcat), name (category|subcat)

    await ch.render_create_item_step_message(message, ch.build_item_description_step_text(), 2, 6)
    # get_back_inline_keyboard("back_to_item_title")


@items_router.message(ItemCreateStates.description)
async def process_item_description(message: Message, state: FSMContext) -> None:
    """Обрабатывает ввод описания объявления"""

    description = ch.extract_item_text_input(message)
    error_msg = ch.validate_item_description(description)

    if error_msg:
        await ch.render_create_item_step_message(message, error_msg, 2, 6) # get_back_inline_keyboard("back_to_item_title")
        return  # остаёмся в том же состоянии (description)

    # Сохраняем описание в FSM
    data = await state.get_data()
    draft = ItemCreateDraft.model_validate(data.get("new_item") or {})
    draft.description = description
    await state.update_data(new_item=draft.model_dump())

    # Переход к следующему шагу
    await state.set_state(ItemCreateStates.price)

    await ch.render_create_item_step_message(message, ch.build_item_price_step_text(), 3, 6)
    # get_back_inline_keyboard("back_to_item_description")


@items_router.message(ItemCreateStates.price)
async def process_item_price(message: Message, state: FSMContext) -> None:
    """Обрабатывает ввод цены аренды (шаг FSM)"""

    price_text = ch.extract_item_money_input(message)

    validation_error, price = ch.validate_item_price(price_text)
    if validation_error:
        await ch.render_create_item_step_message(message, validation_error, 3, 6)  # get_back_inline_keyboard("back_to_item_description"),
        return # остаёмся в том же состоянии (price)

    # Сохраняем цену в FSM
    data = await state.get_data()
    draft = ItemCreateDraft.model_validate(data.get("new_item") or {})
    draft.price = price
    await state.update_data(new_item=draft.model_dump())

    # Переходим к следующему шагу FSM — залог
    await state.set_state(ItemCreateStates.deposit)

    await ch.render_create_item_step_message(message, ch.build_item_deposit_step_text(),4, 6)
    # get_back_inline_keyboard("back_to_item_description")


@items_router.message(ItemCreateStates.deposit)
async def process_item_deposit(message: Message, state: FSMContext) -> None:
    """Обрабатывает ввод суммы залога (шаг FSM)."""

    deposit_text = ch.extract_item_money_input(message)

    validation_error, deposit = ch.validate_item_deposit(deposit_text)
    if validation_error:
        await ch.render_create_item_step_message(message, validation_error, 4, 6) # get_back_inline_keyboard("back_to_item_price")
        return # остаёмся в состоянии deposit

    # Сохраняем сумму залога в FSM
    data = await state.get_data()
    draft = ItemCreateDraft.model_validate(data.get("new_item") or {})
    draft.deposit = deposit
    await state.update_data(new_item=draft.model_dump())

    await state.set_state(ItemCreateStates.location)

    await ch.render_create_item_step_message(message, ch.build_item_location_step_text(),5, 6) # get_back_inline_keyboard("back_to_item_description")


@items_router.message(ItemCreateStates.location)
async def process_item_location(message: Message, state: FSMContext) -> None:
    """Обрабатывает ввод местоположения вещи (шаг FSM)."""

    location = ch.extract_item_text_input(message)

    if len(location) < 3:
        text = "❌ Местоположение слишком короткое. Пожалуйста, укажите хотя бы город/район."
        await ch.render_create_item_step_message(message, text, 5, 6)  # get_back_inline_keyboard("back_to_item_deposit")
        return  # остаёмся в состоянии location

    # Сохраняем местоположение в FSM
    data = await state.get_data()
    draft = ItemCreateDraft.model_validate(data.get("new_item") or {})
    draft.location = location
    await state.update_data(new_item=draft.model_dump())

    # Переходим к следующему шагу FSM — минимальный срок аренды
    await state.set_state(ItemCreateStates.rental_period)

    await ch.render_create_item_step_message(message, ch.build_item_min_period_step_text(),6, 6) # get_back_inline_keyboard("back_to_item_location")


@items_router.message(ItemCreateStates.rental_period)
async def process_item_rental_period(message: Message, state: FSMContext) -> None:
    """Обрабатывает ввод минимального срока аренды и показывает итоговое подтверждение объявления"""

    rental_period = ch.extract_item_text_input(message)

    validation_error, min_days = ch.validate_item_min_period(rental_period)
    if validation_error:
        await ch.render_create_item_step_message(message, validation_error, 6, 6) # get_back_inline_keyboard("back_to_item_location")
        return # остаёмся в состоянии rental_period

    # Сохраняем срок в FSM
    data = await state.get_data()
    draft = ItemCreateDraft.model_validate(data.get("new_item") or {})
    draft.min_rental_period = min_days
    await state.update_data(new_item=draft.model_dump())

    # Переход к шагу загрузки фото
    await state.set_state(ItemCreateStates.photos)

    await message.answer(ch.build_item_photo_step_text(), reply_markup=get_photos_keyboard(), parse_mode="HTML")

# ───────────────────────────────────────── ЛОГИКА ДОБАВЛЕНИЯ ФОТОГРАФИЙ ───────────────────────────────────────────────
@items_router.message(ItemCreateStates.photos, F.text == "✅ Готово")
async def photos_done(message: Message, state: FSMContext):
    """Пользователь завершил загрузку фотографий."""

    data = await state.get_data()
    photos = data.get("photos", []) # держим отдельно от ItemCreateDraft

    if not photos:
        await message.answer(ch.no_photos, parse_mode="HTML")

    # Переходим к финальному подтверждению
    await state.set_state(ItemCreateStates.confirmation)

    await show_item_confirmation(message, state)


@items_router.message(ItemCreateStates.photos, F.photo)
async def process_item_photos(message: Message, state: FSMContext) -> None:
    """Обработка загруженной фотографии. Тут собираем все фото пользователя"""

    data = await state.get_data()
    photos = data.get("photos", [])

    if len(photos) >= MAX_PHOTOS:
        await message.answer(ch.build_item_photo_max_photos_warning(), reply_markup=get_photos_keyboard())
        return

    # Получаем файловый ID фотографии с наилучшим разрешением
    file_id = message.photo[-1].file_id

    # Добавляем фото в список
    photos.append(file_id)
    await state.update_data(photos=photos) # держим отдельно от ItemCreateDraft

    await message.answer(ch.build_item_photo_success_or_more(len(photos)), reply_markup=get_photos_keyboard())


@items_router.message(ItemCreateStates.photos)
async def photos_wrong_input(message: Message):
    """Обработка неверного ввода (не фото и не команда)."""
    await message.answer(ch.photo_or_ready, reply_markup=get_photos_keyboard()) # ✅ Готово / 🔙 Назад   (reply keyboard)

# ───────────────────────────────────────── финальные обработки ────────────────────────────────────────────────────────
async def show_item_confirmation(message: Message, state: FSMContext) -> None:
    """Показывает итоговое подтверждение объявления."""

    data = await state.get_data()
    draft = ItemCreateDraft.model_validate(data.get("new_item") or {})

    category_name, subcategory_name, photos = ch.extract_item_confirmation_context(data)

    # Если есть фото — отправляем фото, либо просто текст
    await ch.send_item_confirmation_preview(
        message=message,
        text=ch.build_item_confirmation_text(draft, category_name, category_name, len(photos)),
        photos=photos,
        keyboard=ch.build_item_confirmation_keyboard()
    )


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
    if not new_item:
        await send_or_edit(callback, ch.data_item_not_found)
        return

    # Валидация Draft
    try:
        draft = ItemCreateDraft.model_validate(new_item)
    except ValidationError:
        await send_or_edit(callback, ch.create_item_valid_err)
        return

    # Финальная валидация Create-схемы (строгий контракт)
    try:
        payload = ItemCreate.model_validate(draft.model_dump())
    except ValidationError:
        await send_or_edit(callback, ch.draft_item_valid_err)
        return

    # Создание объявления (дефолты устанавливает Модель/БД!)
    try:
        created_item = await item_service.create(user_id=user.id, item_data=payload)
    except ServiceError:
        await send_or_edit(callback, ch.cant_create_item_err)
        return

    photos: list[str] = data.get("photos") or []  # data.get("photos", [])
    # сохраняем фотографии отдельно
    if photos:
        await ch.attach_item_photos_or_warn(callback, photo_service, created_item.id, photos)

    await callback.message.answer(
        ch.build_item_created_success_text(created_item.title),
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove(),  # убираем reply-клаву фото
    )

    # очищаем FSM
    await state.clear()

    # 5️⃣ ведём в Мои объявления / главное меню
    #await show_my_items(callback, item_service, user)
    await show_main_menu(callback, user)


# Обработка отмены ❌ публикации объявления
@items_router.callback_query(F.data.startswith(CANCEL_ITEM_CB)) # F.data == CANCEL_ITEM_CB?
async def cancel_flow_to_main_menu(callback: CallbackQuery,  state: FSMContext, user) -> None:
    """❌ Отмена: полностью выходим из FSM, убираем reply-клавиатуру и возвращаем в главное меню."""

    await callback.answer()

    # Полностью очищаем FSM (состояние + данные)
    await state.clear()
    # await state.set_state(None) # 🔄 Очищает состояние, но сохраняет данные. FSM “выйдет” из состояния, но state_data (например, new_item) сохранится
    # await state.update_data(new_item={})  # сбросить только объявление # ✏️ Изменяет/очищает часть данных

    await callback.message.answer(
        "❌ Создание объявления отменено.",
        reply_markup=ReplyKeyboardRemove(), # Убираем reply-клавиатуру
    )

    # Главное меню
    await show_main_menu(callback, user)


# Обработка редактирования ✏️ (логика не завершена)
@items_router.callback_query(F.data.startswith(EDIT_ITEM_CB))
async def start_process_edit_item(callback: CallbackQuery, state: FSMContext, item_service: ItemService) -> None:
    """📝 Начало процесса редактирования объявления"""
    await callback.answer()

    item = await ch.load_entity_or_notify(callback, item_service.get_item_by_id,
                                            parse_callback(callback.data, EDIT_ITEM_CB),
                                            invalid_id_text=ch.not_item_id, load_error_text=ch.serv_err_item,
                                            not_found_text=ch.not_item)

    # Сохраняем данные для редактирования
    await ch.init_edit_item_context(state, item)

    await send_or_edit(
        callback,
        ch.edit_item_start_text(item),
        markup=build_edit_item_keyboard(item.id),
        parse_mode="HTML"
    )

# ────────────────────────────────────────── Редактирования ✏️ объявления ──────────────────────────────────────────────