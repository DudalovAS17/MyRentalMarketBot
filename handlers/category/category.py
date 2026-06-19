from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest

from handlers.category.category_helpers.keyboard import (build_subcategories_keyboard, build_back_to_item_details_keyboard,
                                                         build_items_carousel_keyboard, build_item_details_kb)
from handlers.category.category_helpers.load import resolve_entity, load_list_or_notify
from handlers.category.category_helpers.store import store_selected_category, store_selected_subcategory, store_selected_item
from handlers.category.category_helpers.texts import (item_details_text, not_cat_id, serv_err_cat, not_cat, not_subcat_id,
                                                      serv_err_subcat, not_subcat, not_item_id, not_item, serv_err_item,
                                                      serv_err_photo, not_photos,  subcategory_item_card_text) # serv_err_items

from handlers.category.category_helpers.formatters import busy_until_text, build_photo_media, get_photo_source
from handlers.entries import show_categories
from services.item_service import ItemService
from services.category_service import CategoryService
from services.photo_service import PhotoService
from services.rental_service import RentalService

from schemas.photo import PhotoOut
from utils.functions import send_or_edit, send_reply
from utils.errors import ServiceError
from utils.callbacks import (CAT_CB_PREFIX, SUBCAT_CB_PREFIX, ITEM_DETAILS_CB, SHOW_ALL_PHOTOS_CB, BACK_TO_CAT, CAROUSEL_NAV_CB)
from utils.validators import parse_callback

category_router = Router()

@category_router.callback_query(F.data.startswith(CAT_CB_PREFIX))
async def show_subcategories(callback: CallbackQuery, state: FSMContext, category_service: CategoryService) -> None:
    """Показывает список подкатегорий выбранной категории"""
    await callback.answer()

    category = await resolve_entity(callback, category_service.get_category_by_id, parse_callback(callback.data, CAT_CB_PREFIX),
                                    invalid_id_text=not_cat_id, load_error_text=serv_err_cat, not_found_text=not_cat)
    if category is None:
        return

    # сохраняем выбор категории, сбрасываем подкатегорию
    await store_selected_category(state, category)

    not_subcats = f"⚠️ В категории <b>{category.name}</b> пока нет подкатегорий."
    subcategories = await load_list_or_notify(callback, category_service.list_subcategories, category.id,
                                              invalid_id_text=not_cat_id, load_error_text=serv_err_cat,
                                              not_found_text=not_subcats)
    if subcategories is None:
        return

    await send_or_edit(
        callback,
        f"🔍 <b>Поиск в категории {category.name}</b>\n\n Выберите подкатегорию:",
        markup=build_subcategories_keyboard(subcategories, category)
    )


@category_router.callback_query(F.data.startswith(SUBCAT_CB_PREFIX))
async def show_items_in_subcategory(
    callback: CallbackQuery,
    state: FSMContext,
    item_service: ItemService,
    category_service: CategoryService,
    photo_service: PhotoService,
) -> None:
    """Показывает список товаров в выбранной подкатегории"""
    await callback.answer()

    subcategory = await resolve_entity(callback, category_service.get_category_by_id,
                                       parse_callback(callback.data, SUBCAT_CB_PREFIX),
                                       invalid_id_text=not_subcat_id, load_error_text=serv_err_subcat, not_found_text=not_subcat)
    if subcategory is None:
        return

    # Сохраняем в контекст выбранную подкатегорию
    await store_selected_subcategory(state, subcategory)

    not_items = f"⚠️ В подкатегории <b>{subcategory.name}</b> пока нет товаров."
    items = await load_list_or_notify(callback, item_service.list_items_by_subcategory, subcategory.id,
                                      invalid_id_text=not_subcat_id, load_error_text=serv_err_item,
                                      not_found_text=not_items)
    if items is None:
        return

    # карусель
    current_index = 0
    current_item = items[current_index]
    keyboard = build_items_carousel_keyboard(
        current_item_id=current_item.id,
        subcategory_id=subcategory.id,
        parent_category_id=subcategory.parent_id,
        current_index=current_index,
        total_items=len(items),
        nav_cb_prefix=CAROUSEL_NAV_CB,
        item_details_cb_prefix=ITEM_DETAILS_CB,
        subcat_cb_prefix=SUBCAT_CB_PREFIX,
        cat_cb_prefix=CAT_CB_PREFIX,
    )

    photos = await photo_service.get_photos_by_item_id(current_item.id)
    characteristics = await item_service.list_item_characteristics_by_item_id(current_item.id, limit=3)

    await send_or_edit_item_card(
        callback=callback,
        photos=photos,
        text=subcategory_item_card_text(current_item, current_index, len(items), characteristics),
        markup=keyboard,
    )

    #await send_or_edit(callback, subcategory_item_card_text(current_item, current_index, len(items)), markup=keyboard)


# карусель
@category_router.callback_query(F.data.startswith(CAROUSEL_NAV_CB))
async def navigate_items_carousel(
    callback: CallbackQuery,
    item_service: ItemService,
    category_service: CategoryService,
    photo_service: PhotoService
) -> None:
    """Навигация по карточкам товаров внутри подкатегории."""
    await callback.answer()

    try:
        payload = callback.data.removeprefix(CAROUSEL_NAV_CB)
        subcategory_id_str, index_str = payload.split(":", maxsplit=1)
        subcategory_id = int(subcategory_id_str)
        current_index = int(index_str)
    except (ValueError, AttributeError):
        await callback.answer(not_subcat_id, show_alert=True)
        return

    subcategory = await resolve_entity(
        callback,
        category_service.get_category_by_id,
        subcategory_id,
        invalid_id_text=not_subcat_id,
        load_error_text=serv_err_subcat,
        not_found_text=not_subcat,
    )
    if subcategory is None:
        return

    not_items = f"⚠️ В подкатегории <b>{subcategory.name}</b> пока нет товаров."
    items = await load_list_or_notify(callback, item_service.list_items_by_subcategory, subcategory.id,
                                      invalid_id_text=not_subcat_id, load_error_text=serv_err_item, not_found_text=not_items)
    if items is None:
        return

    total = len(items)
    if total == 0:
        await send_or_edit(callback, not_items) # ?
        return

    current_index = current_index % total
    current_item = items[current_index]

    keyboard = build_items_carousel_keyboard(
        current_item_id=current_item.id,
        subcategory_id=subcategory.id,
        parent_category_id=subcategory.parent_id,
        current_index=current_index,
        total_items=total,
        nav_cb_prefix=CAROUSEL_NAV_CB,
        item_details_cb_prefix=ITEM_DETAILS_CB,
        subcat_cb_prefix=SUBCAT_CB_PREFIX,
        cat_cb_prefix=CAT_CB_PREFIX,
    )

    photos = await photo_service.get_photos_by_item_id(current_item.id)
    characteristics = await item_service.list_item_characteristics_by_item_id(current_item.id, limit=3)

    await send_or_edit_item_card(
        callback=callback,
        photos=photos,
        text=subcategory_item_card_text(current_item, current_index, len(items), characteristics),
        markup=keyboard,
    )

    #await send_or_edit(callback, subcategory_item_card_text(current_item, current_index, total), markup=keyboard)


@category_router.callback_query(F.data.startswith(ITEM_DETAILS_CB))
async def show_item_details_in_subcategory(
    callback: CallbackQuery,
    state: FSMContext,
    item_service: ItemService,
    rental_service: RentalService,
) -> None:
    """Просмотр карточки конкретного товара"""
    await callback.answer()

    item = await resolve_entity(callback, item_service.get_item_by_id, parse_callback(callback.data, ITEM_DETAILS_CB),
                                     invalid_id_text=not_item_id, load_error_text=serv_err_item, not_found_text=not_item)
    if item is None:
        return

    # Сохраняем в контекст выбранный товар - возможно избыточно
    await store_selected_item(state, item.id)

    data = await state.get_data()
    category_name = data.get("selected_category_name", "Неизвестно")
    subcategory_name = data.get("selected_subcategory_name", "Неизвестно")
    selected_subcategory_id = data.get("selected_subcategory_id")

    # Формируем детальную информацию
    characteristics = await item_service.list_item_characteristics_by_item_id(item.id, limit=3)
    item_details = item_details_text(item, category_name, subcategory_name, characteristics)

    # Проверяем занятость (если есть активная/открытая аренда)
    try:
        open_rental = await rental_service.get_open_rental_for_item(item.id)
    except ServiceError:
        open_rental = None  # если проверка не удалась — не блокируем UX

    keyboard = build_item_details_kb(
        item_id=item.id,
        is_busy=open_rental is not None,
        selected_subcategory_id=selected_subcategory_id,
        end_date=busy_until_text(open_rental)
    )

    await send_or_edit(callback, item_details, markup=keyboard)


@category_router.callback_query(F.data == BACK_TO_CAT)
async def back_to_categories(callback: CallbackQuery, category_service: CategoryService) -> None:
    """Кнопка '🔙 Назад' → возвращаемся к списку категорий"""
    await show_categories(callback, category_service)



@category_router.callback_query(F.data.startswith(SHOW_ALL_PHOTOS_CB))
async def show_all_photos(callback: CallbackQuery, photo_service: PhotoService) -> None:
    """Показать все фотографии товара"""
    await callback.answer()

    item_id = parse_callback(callback.data, SHOW_ALL_PHOTOS_CB)
    photos = await load_list_or_notify(callback, photo_service.get_photos_by_item_id, item_id, invalid_id_text=not_item_id,
                                       load_error_text=serv_err_photo, not_found_text=not_photos)
    if photos is None:
        return

    # Отправляем альбом (это всегда новое сообщение)
    media = build_photo_media(photos)
    if not media:
        await send_or_edit(
            callback,
            "⚠️ У этого товара пока нет доступных фото.",
            markup=build_back_to_item_details_keyboard(item_id),
        )
        return

    if callback.message is None:
        await callback.answer("⚠️ Не удалось открыть фото товара.", show_alert=True) # ?
        return

    # UX: убрать прошлый экран
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass

    await callback.message.answer_media_group(media)

    await send_reply(
        callback,
        "📸 <b>Все фото товара</b>",
        markup=build_back_to_item_details_keyboard(item_id)
    )


# ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
async def send_or_edit_item_card(callback: CallbackQuery, photos: list[PhotoOut], text: str, markup) -> None:
    """Показать карточку товара: с фото, если оно есть, иначе обычным текстом."""
    main_photo = photos[0] if photos else None
    photo_source = get_photo_source(main_photo)

    if not photo_source:
        await send_or_edit(callback, text, markup=markup)
        return

    message = callback.message
    if message is None:
        return

    try:
        # Если текущее сообщение уже с фото — редактируем media.
        if message.photo:
            from aiogram.types import InputMediaPhoto

            await message.edit_media(
                media=InputMediaPhoto(
                    media=photo_source,
                    caption=text,
                    parse_mode="HTML",
                ),
                reply_markup=markup,
            )
            return

        # Если текущее сообщение текстовое — удаляем его и отправляем фото.
        await message.delete()
        await message.answer_photo(
            photo=photo_source,
            caption=text,
            reply_markup=markup,
            parse_mode="HTML",
        )

    except TelegramBadRequest:
        # Fallback: если Telegram не смог отредактировать/удалить сообщение.
        await message.answer_photo(
            photo=photo_source,
            caption=text,
            reply_markup=markup,
            parse_mode="HTML",
        )