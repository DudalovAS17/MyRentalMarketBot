from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext

#from .router import

from handlers.admin import create_item_helpers as ch
from handlers.entries import show_main_menu
from services.item_service import ItemService
from services.photo_service import PhotoService
from services.category_service import CategoryService
from schemas.item import ItemCreateDraft, ItemCreate
from states.item import ItemCreateStates
from keyboards.item_kb import get_photos_keyboard, cancel_keyboard
from utils.functions import send_or_edit
from utils.errors import ServiceError, ValidationError
from utils.validators import parse_callback
from utils.callbacks import (ADMIN_CAT_FI_PREFIX, ADMIN_SUBCAT_FI_PREFIX, ADMIN_ADD_ITEM_CB, ADMIN_PUBLISH_ITEM_CB,
                             ADMIN_CANCEL_ITEM_CB, ADMIN_MAX_PHOTOS, ADMIN_CREATE_ITEM_MODE) #, BACK_TO_MENU_CB, BACK_TO_CAT

admin_create_item_router = Router()

# ***** кнопка админки "+Создать товар" *****

# ─────────────────────────────────────────────── helpers ──────────────────────────────────────────────────────────────
async def _save_draft(state: FSMContext, draft: ItemCreateDraft) -> None:
    await state.update_data(new_item=draft.model_dump())

async def _get_draft(state: FSMContext) -> ItemCreateDraft:
    data = await state.get_data()
    return ItemCreateDraft.model_validate(data.get("new_item") or {})

# ─────────────────────────────────────────────── Основной FSM ─────────────────────────────────────────────────────────
@admin_create_item_router.callback_query(F.data == ADMIN_ADD_ITEM_CB)
async def start_create_item_by_admin(callback: CallbackQuery, state: FSMContext, category_service: CategoryService, user) -> None:
    """FSM: Запуск процесса создания товара из админки"""
    await callback.answer()

    # Очистим все предыдущие данные (data сейчас: пусто)
    await state.clear()

    # Инициализация FSM (Фото держим отдельно от ItemCreateDraft)
    await state.update_data(
        mode=ADMIN_CREATE_ITEM_MODE,
        admin_user_id=user.id,
        new_item=ItemCreateDraft().model_dump(),
        photos=[]
    )

    # Переводим FSM в первое состояние - выбор категории
    await state.set_state(ItemCreateStates.category)

    # Показываем категории
    await ch.show_create_item_categories_step(callback, category_service)

@admin_create_item_router.callback_query(F.data.startswith(ADMIN_CAT_FI_PREFIX))
async def show_subcategories_for_creating_item(callback: CallbackQuery, state: FSMContext, category_service: CategoryService) -> None:
    """FSM: Показывает подкатегории."""
    await callback.answer()

    category = await ch.load_entity_or_notify(
        callback, category_service.get_category_by_id, parse_callback(callback.data, ADMIN_CAT_FI_PREFIX),
        invalid_id_text=ch.not_cat_id, load_error_text=ch.serv_err_cat, not_found_text=ch.not_cat
    )
    if category is None:
        return

    subcategories = await ch.load_entity_or_notify(
        callback, category_service.list_subcategories, category.id, invalid_id_text=ch.not_cat_id,
        load_error_text=ch.serv_err_cat, not_found_text=ch.not_subcats(category.name)
    )
    if subcategories is None:
        return

    # Сохраняем категорию
    await ch.store_selected_category(state, category)

    # Переводим FSM во второе состояние - выбор подкатегории
    await state.set_state(ItemCreateStates.subcategory)

    # Показываем подкатегории
    await send_or_edit(
        callback,
        ch.create_item_subcategory_step_text(category.name),
        markup=ch.build_create_item_subcategories_keyboard(subcategories)
    )

@admin_create_item_router.callback_query(F.data.startswith(ADMIN_SUBCAT_FI_PREFIX))
async def start_create_item_from_subcategory(callback: CallbackQuery, state: FSMContext, category_service: CategoryService) -> None:
    """FSM: Переход из подкатегории к вводу названия товара"""
    await callback.answer()

    subcategory = await ch.load_entity_or_notify(
        callback, category_service.get_category_by_id, parse_callback(callback.data, ADMIN_SUBCAT_FI_PREFIX),
        invalid_id_text=ch.not_subcat_id, load_error_text=ch.serv_err_subcat, not_found_text=ch.not_subcat
    )
    if subcategory is None:
        return

    # достаем категорию из state
    data = await state.get_data()
    category_id = data.get("selected_category_id")

    if not category_id: # пробуем получить категория из подкатегории
        category_id = subcategory.parent_id

    category = await ch.load_entity_or_notify(
        callback, category_service.get_category_by_id, category_id, invalid_id_text=ch.not_cat_id,
        load_error_text=ch.serv_err_cat, not_found_text=ch.not_cat
    )
    if category is None:
        return

    # Валидируем черновик из FSM
    draft = ItemCreateDraft.model_validate(data.get("new_item") or {})

    # обновляем FSM данными
    draft.category_id = category_id
    draft.subcategory_id = subcategory.id

    # Сохраняем подкатегорию
    await ch.store_selected_subcategory(state=state, category=category, subcategory=subcategory, draft=draft)

    # Показываем приглашение ввести название вещи
    await start_create_item_title(callback, state, category, subcategory)

async def start_create_item_title(event: Message | CallbackQuery, state: FSMContext, category=None, subcategory=None) -> None:
    """FSM: приглашение ввести название товара"""

    # переводим FSM в состояние ожидания названия
    await state.set_state(ItemCreateStates.title)

    await send_or_edit(event, ch.create_new_item_text(category, subcategory), markup=cancel_keyboard())

@admin_create_item_router.message(ItemCreateStates.title)
async def process_item_title(message: Message, state: FSMContext) -> None:
    """FSM: Обрабатывает ввод названия при создании товара + приглашение ввести описание товара."""

    title = ch.extract_item_text_input(message)

    error_msg = ch.validate_item_title(title)
    if error_msg:
        await ch.render_create_item_step_message(message, error_msg, 1, 5)
        return # остаёмся в том же состоянии (title)

    # сохраняем во временное хранилище FSM
    draft = await _get_draft(state)
    draft.title = title
    await _save_draft(state, draft)

    # переводим FSM в следующее состояние
    await state.set_state(ItemCreateStates.description)

    await ch.render_create_item_step_message(message, ch.build_item_description_step_text(), 2, 5)

@admin_create_item_router.message(ItemCreateStates.description)
async def process_item_description(message: Message, state: FSMContext) -> None:
    """FSM: Обрабатывает ввод описания товара + приглашение ввести цену товара."""

    description = ch.extract_item_text_input(message)

    error_msg = ch.validate_item_description(description)
    if error_msg:
        await ch.render_create_item_step_message(message, error_msg, 2, 5)
        return  # остаёмся в том же состоянии (description)

    # Сохраняем описание в FSM
    draft = await _get_draft(state)
    draft.description = description
    await _save_draft(state, draft)

    # Переход к следующему шагу
    await state.set_state(ItemCreateStates.price)

    await ch.render_create_item_step_message(message, ch.build_item_price_step_text(), 3, 5)

@admin_create_item_router.message(ItemCreateStates.price)
async def process_item_price(message: Message, state: FSMContext) -> None:
    """FSM: Обрабатывает ввод цены аренды + приглашение ввести количество товара."""

    price_text = ch.extract_item_money_input(message)

    validation_error, price = ch.validate_item_price(price_text)
    if validation_error:
        await ch.render_create_item_step_message(message, validation_error, 3, 5)
        return # остаёмся в том же состоянии (price)

    # Сохраняем цену в FSM
    draft = await _get_draft(state)
    draft.price = price
    await _save_draft(state, draft)

    # Переходим к следующему шагу FSM — залог
    await state.set_state(ItemCreateStates.available_quantity)

    await ch.render_create_item_step_message(message, ch.build_item_available_quantity_step_text(),4, 5)

# перешел от deposit -> available_quantity
@admin_create_item_router.message(ItemCreateStates.available_quantity)
async def process_item_quantity(message: Message, state: FSMContext) -> None:
    """FSM: Обрабатывает ввод количество товара + приглашение ввести период аренды."""

    quantity_text = ch.extract_item_available_quantity_input(message)

    validation_error, quantity = ch.validate_item_available_quantity(quantity_text)
    if validation_error:
        await ch.render_create_item_step_message(message, validation_error, 4, 5)
        return # остаёмся в состоянии quantity

    # Сохраняем сумму залога в FSM
    draft = await _get_draft(state)
    draft.available_quantity = quantity
    await _save_draft(state, draft)

    # Переходим к следующему шагу FSM — минимальный срок аренды
    await state.set_state(ItemCreateStates.rental_period)

    await ch.render_create_item_step_message(message, ch.build_item_min_period_step_text(),5, 5)

@admin_create_item_router.message(ItemCreateStates.rental_period)
async def process_item_rental_period(message: Message, state: FSMContext) -> None:
    """FSM: Обрабатывает ввод периода аренды + показывает итоговое подтверждение объявления."""

    rental_period = ch.extract_item_text_input(message)

    validation_error, min_days = ch.validate_item_min_period(rental_period)
    if validation_error:
        await ch.render_create_item_step_message(message, validation_error, 5, 5)
        return # остаёмся в состоянии rental_period

    # Сохраняем сумму залога в FSM
    draft = await _get_draft(state)
    draft.min_rental_period = min_days
    await _save_draft(state, draft)

    # Переход к шагу загрузки фото
    await state.set_state(ItemCreateStates.photos)

    await message.answer(ch.build_item_photo_step_text(), reply_markup=get_photos_keyboard(), parse_mode="HTML")

# ───────────────────────────────────────── ДОБАВЛЕНИЯ ФОТОГРАФИЙ ──────────────────────────────────────────────────────
@admin_create_item_router.message(ItemCreateStates.photos, F.text == "✅ Готово")
async def photos_done(message: Message, state: FSMContext):
    """FSM: Админ завершил загрузку фотографий"""

    data = await state.get_data()

    photos = data.get("photos")
    if not photos:
        await message.answer(ch.no_photos, parse_mode="HTML")

    # Переходим к финальному подтверждению
    await state.set_state(ItemCreateStates.confirmation)

    await show_item_confirmation(message, state)

@admin_create_item_router.message(ItemCreateStates.photos, F.photo)
async def process_item_photos(message: Message, state: FSMContext) -> None:
    """FSM: Обработка загруженной фотографии. Тут собираем все фото пользователя"""

    data = await state.get_data()
    photos: list[str] = data.get("photos") or []

    if len(photos) >= ADMIN_MAX_PHOTOS:
        await message.answer(ch.build_item_photo_max_photos_warning(), reply_markup=get_photos_keyboard())
        return

    # Получаем файловый ID фотографии с наилучшим разрешением
    file_id = message.photo[-1].file_id

    # Добавляем фото в список
    photos.append(file_id)
    await state.update_data(photos=photos)

    await message.answer(ch.build_item_photo_success_or_more(len(photos)), reply_markup=get_photos_keyboard())

@admin_create_item_router.message(ItemCreateStates.photos)
async def photos_wrong_input(message: Message):
    """FSM: Обработка неверного ввода (не фото и не команда)"""
    await message.answer(ch.photo_or_ready, reply_markup=get_photos_keyboard())

# ───────────────────────────────────────── ФИНАЛЬНЫЕ ОБРАБОТКИ ────────────────────────────────────────────────────────
async def show_item_confirmation(message: Message, state: FSMContext) -> None:
    """Показывает итоговое подтверждение товара"""

    data = await state.get_data()
    draft = ItemCreateDraft.model_validate(data.get("new_item") or {})

    category_name, subcategory_name, photos = ch.extract_item_confirmation_context(data)

    # Если есть фото — отправляем фото, либо просто текст
    await ch.send_item_confirmation_preview(
        message=message,
        text=ch.build_item_confirmation_text(draft, category_name, subcategory_name, len(photos)),
        photos=photos,
        keyboard=ch.build_item_confirmation_keyboard()
    )

@admin_create_item_router.callback_query(F.data.startswith(ADMIN_PUBLISH_ITEM_CB))
async def process_item_confirmation(
        callback: CallbackQuery,
        state: FSMContext,
        item_service: ItemService,
        photo_service: PhotoService,
        user
) -> None:
    """FSM: Обрабатывает подтверждение создания товара - ПУБЛИКАЦИЯ ТОВАРА"""
    await callback.answer()

    data = await state.get_data()
    new_item = data.get("new_item")
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

    # Создание товара
    try:
        created_item = await item_service.create(item_data=payload, created_by_admin_id=user.id)
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
        reply_markup=ReplyKeyboardRemove(),
    )

    # очищаем FSM
    await state.clear()

    # ведём в главное меню
    await show_main_menu(callback, user)

@admin_create_item_router.callback_query(F.data.startswith(ADMIN_CANCEL_ITEM_CB))
async def cancel_flow_to_main_menu(callback: CallbackQuery,  state: FSMContext, user) -> None:
    """Обработка отмены ❌ публикации товара"""
    await callback.answer()

    # Полностью очищаем FSM (состояние + данные)
    await state.clear()

    await callback.message.answer(
        "❌ Создание товара отменено.",
        reply_markup=ReplyKeyboardRemove(),
    )

    # Главное меню
    await show_main_menu(callback, user)