import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest

from handlers.category.category_helpers.keyboard import build_subcategories_keyboard, build_back_to_item_details_keyboard
from handlers.category.category_helpers.load import resolve_entity, load_entity_or_notify
from handlers.category.category_helpers.store import store_selected_category, store_selected_subcategory, store_selected_item
from handlers.category.category_helpers.texts import (item_details_text, not_cat_id, serv_err_cat, not_cat, not_subcat_id,
                                                      serv_err_subcat, not_subcat, not_item_id, not_item, serv_err_item,
                                                      serv_err_photo, not_photos) # serv_err_items

from handlers.category.category_helpers.validate import busy_until_text, build_photo_media
from handlers.entries.category_entry import show_categories
from services.item_service import ItemService
from services.category_service import CategoryService
from services.photo_service import PhotoService
from services.rental_service import RentalService

from keyboards.category_kb import build_items_keyboard, build_item_details_kb
from utils.functions import send_or_edit, send_reply
from utils.errors import ServiceError
from utils.callbacks import (CAT_CB_PREFIX, SUBCAT_CB_PREFIX, ITEM_DETAILS_CB, SHOW_ALL_PHOTOS_CB, BACK_TO_CAT)
from utils.validators import parse_callback

logger = logging.getLogger(__name__)
category_router = Router()

# 🧱 ⚙️ ────────────────────────────────────────────────────────────────────────────────────────────────────────────────
@category_router.callback_query(F.data == BACK_TO_CAT)
async def back_to_categories(callback: CallbackQuery, category_service: CategoryService) -> None:
    """Кнопка '🔙 Назад' → возвращаемся к списку категорий."""
    await show_categories(callback, category_service)


@category_router.callback_query(F.data.startswith(CAT_CB_PREFIX))
async def show_subcategories(callback: CallbackQuery, state: FSMContext, category_service: CategoryService) -> None:
    """Показывает список подкатегорий выбранной категории"""
    await callback.answer()

    category = await resolve_entity(callback, category_service.get_category, parse_callback(callback.data, CAT_CB_PREFIX),
                                     invalid_id_text=not_cat_id, load_error_text=serv_err_cat, not_found_text=not_cat)

    # UX-контекст: сохраняем выбор категории, сбрасываем подкатегорию
    await store_selected_category(state, category)

    not_subcats = f"⚠️ В категории <b>{category.name}</b> пока нет подкатегорий."
    subcategories = await load_entity_or_notify(callback, category_service.list_subcategories, category.id,
                                                 invalid_id_text=not_cat_id, load_error_text=serv_err_cat, not_found_text=not_subcats)

    subcategories = subcategories or []
    await send_or_edit(
        callback,
        f"🔍 <b>Поиск в категории {category.name}</b>\n\n Выберите подкатегорию:",
        markup=build_subcategories_keyboard(subcategories, category)
    )
    # data сейчас: id (category), name (category)


@category_router.callback_query(F.data.startswith(SUBCAT_CB_PREFIX))
async def show_items_in_subcategory(
    callback: CallbackQuery,
    state: FSMContext,
    item_service: ItemService,
    category_service: CategoryService,
    #limit: int = 10
) -> None:
    """Показывает список объявлений в выбранной подкатегории (limit: ограничение по количеству объявлений)"""
    await callback.answer()

    subcategory = await resolve_entity(callback, category_service.get_category,
                                        parse_callback(callback.data, SUBCAT_CB_PREFIX),
                                        invalid_id_text=not_subcat_id, load_error_text=serv_err_subcat, not_found_text=not_subcat)

    # Сохраняем в контекст выбранную подкатегорию
    await store_selected_subcategory(state, subcategory)

    not_items = f"⚠️ В подкатегории <b>{subcategory.name}</b> пока нет объявлений."
    items = await load_entity_or_notify(callback, item_service.list_by_subcategory, subcategory.id,
                                                 invalid_id_text=not_subcat_id, load_error_text=serv_err_item, not_found_text=not_items)

    items = items or []
    keyboard = build_items_keyboard(
        items,
        parent_category_id=subcategory.parent_id,
        item_details_cb_prefix=ITEM_DETAILS_CB,
        cat_cb_prefix=CAT_CB_PREFIX,
    )
    message_text = f"📋 Объявления в подкатегории <b>{subcategory.name}</b>\n\n Выберите объявление:"
    await send_or_edit(callback, message_text, markup=keyboard)
    # data сейчас: id (category|subcategory), name (category|subcategory)


@category_router.callback_query(F.data.startswith(ITEM_DETAILS_CB))
async def show_item_details_in_subcategory(
    callback: CallbackQuery,
    state: FSMContext,
    item_service: ItemService,
    #photo_service: PhotoService,
    rental_service: RentalService,
) -> None:
    """Просмотр всех деталей конкретного объявления"""
    await callback.answer()

    item = await resolve_entity(callback, item_service.get_item_by_id, parse_callback(callback.data, ITEM_DETAILS_CB),
                                     invalid_id_text=not_item_id, load_error_text=serv_err_item, not_found_text=not_item)

    # Сохраняем в контекст выбранное объявление - возможно избыточно
    await store_selected_item(state, item.id)

    data = await state.get_data()
    category_name = data.get("selected_category_name", "Неизвестно") # data.get() or "—"
    subcategory_name = data.get("selected_subcategory_name", "Неизвестно") # data.get() or "—"
    selected_subcategory_id = data.get("selected_subcategory_id")

    # Формируем детальную информацию
    item_details = item_details_text(item, category_name, subcategory_name)

    # Проверяем занятость (если есть активная/открытая аренда)
    try:
        open_rental = await rental_service.get_open_rental_for_item(item.id)
    except ServiceError:
        open_rental = None  # если проверка не удалась — не блокируем UX

    keyboard = build_item_details_kb(
        item_id=item.id,
        is_busy=open_rental is not None,
        selected_subcategory_id=selected_subcategory_id,
        end_date = busy_until_text(open_rental)
    )

    # Логика "отправляем главное фото" - возможно реализуем позже

    await send_or_edit(callback, item_details, markup=keyboard)
    # data сейчас: id (category|subcategory|item), name (category|subcategory)


@category_router.callback_query(F.data.startswith(SHOW_ALL_PHOTOS_CB))
async def show_all_photos(callback: CallbackQuery, photo_service: PhotoService) -> None: # state: FSMContext,
    """Показать все фотографии объявления (альбомом)."""
    await callback.answer()

    # Логика: "если уже показывали" — пока оставим это.

    item_id = parse_callback(callback.data, SHOW_ALL_PHOTOS_CB)
    photos = await load_entity_or_notify(callback, photo_service.get_photos, item_id,
                                         invalid_id_text=not_item_id, load_error_text=serv_err_photo, not_found_text=not_photos)

    # UX: стараемся убрать прошлый экран. Это не обязательно - но удобно.
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass

    # Отправляем альбом (это всегда новое сообщение)
    photos = photos or []
    #media = []
    #for p in photos:
    #    media.append(InputMediaPhoto(media=p.telegram_file_id))
    media = build_photo_media(photos)
    await callback.message.answer_media_group(media)

    await send_reply(
        callback,
        "📸 <b>Все фото объявления</b>",
        markup=build_back_to_item_details_keyboard(item_id)
    )
    # data сейчас: id (category|subcategory|item), name (category|subcategory)