import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest

from services.item_service import ItemService
from services.category_service import CategoryService
from services.photo_service import PhotoService
from services.rental_service import RentalService
from handlers.entries.category_entry import show_categories

from keyboards.category_kb import build_category_keyboard, build_items_keyboard, build_item_details_kb
from utils.functions import format_price, send_or_edit, send_reply, format_days
from utils.errors import ServiceError

from utils.callbacks import (CAT_CB_PREFIX, SUBCAT_CB_PREFIX, ITEM_DETAILS_CB, SHOW_ALL_PHOTOS_CB, BACK_TO_CAT, # обработаны тут
                             ALL_CATEGORY_CB, SEARCH_CITY_CB, SEARCH_FILTERS_CB, # будут обработаны в хендлере Search
                             BACK_TO_MENU_CB) # где?

logger = logging.getLogger(__name__)
category_router = Router()

# 🧱 ⚙️
# UX-ответ без stacktrace пользователю

@category_router.callback_query(F.data == BACK_TO_CAT)
async def back_to_categories(callback: CallbackQuery, category_service: CategoryService) -> None:
    """Кнопка '🔙 Назад' → возвращаемся к списку категорий."""
    await show_categories(callback, category_service)


@category_router.callback_query(F.data.startswith(CAT_CB_PREFIX))
async def show_subcategories(callback: CallbackQuery, state: FSMContext, category_service: CategoryService) -> None:
    """Показывает список подкатегорий выбранной категории"""

    await callback.answer()

    try:
        category_id = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        await send_or_edit(callback,"⚠️ Не удалось распознать категорию.")
        return

    category = await _resolve_category(callback, category_service, category_id)

    # UX-контекст: сохраняем выбор категории, сбрасываем подкатегорию
    await _store_selected_category(state, category)

    subcategories = _load_subcategories_or_notify(callback, category_service, category_id, category.name)

    subcategories = subcategories or []

    keyboard = build_category_keyboard(
        subcategories,
        prefix=SUBCAT_CB_PREFIX,
        extra_buttons=[
            [InlineKeyboardButton(text=f"📋 Все в категории {category.name}",
                                  callback_data=f"{ALL_CATEGORY_CB}:{category.id}")],
            [InlineKeyboardButton(text="🔙 Назад (к категориям)", callback_data=BACK_TO_CAT)]
        ]
    )
    # Идея: Добавляем кнопки для каждой подкатегории

    text = f"🔍 <b>Поиск в категории {category.name}</b>\n\n Выберите подкатегорию:"

    await send_or_edit(callback, text, markup=keyboard)
    # data сейчас: id (category), name (category)


@category_router.callback_query(F.data.startswith(SUBCAT_CB_PREFIX))
async def show_items_in_subcategory(
    callback: CallbackQuery,
    state: FSMContext,
    item_service: ItemService,
    category_service: CategoryService,
    #limit: int = 10
) -> None:
    """Показывает список объявлений в выбранной подкатегории
        limit: ограничение по количеству объявлений"""

    await callback.answer()

    try:
        subcategory_id = int(callback.data.split(":")[1]) # .split(":", 1)[1]
    except (IndexError, ValueError):
        await send_or_edit(callback,"⚠️ Не удалось распознать подкатегорию.")
        return

    try:
        subcategory = await category_service.get_category(subcategory_id)
    except ServiceError:
        await send_or_edit(callback, "⚠️ Не удалось загрузить подкатегорию. Попробуйте позже.")
        return

    if not subcategory:
        await callback.answer("⚠️ Подкатегория не найдена", show_alert=True)
        return # await show_categories(callback, category_service)

    # Сохраняем в контекст выбранную подкатегорию
    await state.update_data(
        selected_subcategory_id=subcategory.id,
        selected_subcategory_name=subcategory.name
    )

    # получаем список объявлений по подкатегории
    try:
        items = await item_service.list_by_subcategory(subcategory_id) # , limit=limit
    except ServiceError:
        await send_or_edit(callback, "⚠️ Не удалось загрузить объявления. Попробуйте позже.")
        return

    items = items or []
    if not items:
        message_text = f"⚠️ В подкатегории <b>{subcategory.name}</b> пока нет объявлений."
        await send_or_edit(callback, message_text)
        return

    # строим клавиатуру объявлений
    keyboard = build_items_keyboard(
        items,
        parent_category_id=subcategory.parent_id,
        item_details_cb_prefix=ITEM_DETAILS_CB,  # "show_item_details:"
        cat_cb_prefix=CAT_CB_PREFIX,  # "cat:"
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

    try:
        item_id = int(callback.data.split(":")[1]) # .split(":", 1)
    except (IndexError, ValueError):
        await send_or_edit(callback,"⚠️ Не удалось распознать объявление.")
        return

    # Получаем объявление
    try:
        item = await item_service.get_item_by_id(item_id)
    except ServiceError:
        await send_or_edit(callback, "⚠️ Не удалось загрузить объявление. Попробуйте позже.")
        return

    if not item:
        await callback.answer("⚠️ Объявление не найдено", show_alert=True)
        return # await show_categories(callback, category_service)

    # Сохраняем в контекст выбранное объявление - возможно избыточно
    await state.update_data(
        selected_item_id=item.id
    )

    data = await state.get_data()
    category_name = data.get("selected_category_name", "Неизвестно")
    subcategory_name = data.get("selected_subcategory_name", "Неизвестно")
    #category_name = data.get("selected_category_name") or "—"
    #subcategory_name = data.get("selected_subcategory_name") or "—"

    # Формируем детальную информацию
    item_details = _item_details_text(item, category_name, subcategory_name)

    # Проверяем занятость (если есть активная/открытая аренда)
    try:
        open_rental = await rental_service.get_open_rental_for_item(item_id)
    except ServiceError:
        open_rental = None  # если проверка не удалась — не блокируем UX

    is_busy = open_rental is not None

    # Клавиатура
    selected_subcategory_id = data.get("selected_subcategory_id")

    busy_until = (
        open_rental.end_date.strftime("%d.%m.%Y")
        if open_rental and open_rental.end_date
        else None
    )

    keyboard = build_item_details_kb(
        item_id=item.id,
        is_busy=is_busy,
        selected_subcategory_id=selected_subcategory_id,
        end_date = busy_until
    )

    """ Логика хорошая и рабочая - но исполнение плохое - возможно реализуем позже
        # ======== ФОТО =========
        try:
            photos = await photo_service.get_photos(item_id)
        except ServiceError:
            photos = []

        # UX: стараемся убрать прошлый экран. Это не обязательно, но удобно.
        try:
            await callback.message.delete()
        except TelegramBadRequest:
            pass

        if photos:
            # отправляем главное фото
            await callback.message.answer_photo(
                photo=photos[0].telegram_file_id,
                caption=item_details,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        else:
            # без фото
            await callback.message.answer( # edit_text
                item_details,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        """

    await send_or_edit(callback, item_details, markup=keyboard)
    # data сейчас: id (category|subcategory|item), name (category|subcategory)


@category_router.callback_query(F.data.startswith(SHOW_ALL_PHOTOS_CB))
async def show_all_photos(callback: CallbackQuery, photo_service: PhotoService) -> None: # state: FSMContext,
    """Показать все фотографии объявления (альбомом)."""
    await callback.answer()

    try:
        item_id = int(callback.data.split(":")[1]) # .split(":", 1)
    except (IndexError, ValueError):
        await send_or_edit(callback, "⚠️ Не удалось распознать объявление.")
        return

    # Логика: "если уже показывали" — пока оставим это.

    # Получаем все фото объявления
    try:
        photos = await photo_service.get_photos(item_id)
    except ServiceError:
        await send_or_edit(callback, "⚠️ Не удалось загрузить фото. Попробуйте позже.")
        return

    photos = photos or []
    if not photos:
        await send_or_edit(callback, "⚠️ Фото для этого объявления не найдены.") # 📭 У этого объявления нет фотографий
        return

    media = []
    for p in photos:
        media.append(
            InputMediaPhoto(media=p.telegram_file_id)
        )

    # UX: стараемся убрать прошлый экран. Это не обязательно - но удобно.
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass

    # Отправляем альбом (это всегда новое сообщение)
    await callback.message.answer_media_group(media)

    # отправляем кнопку назад
    back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад (к деталям объявления)", callback_data=f"{ITEM_DETAILS_CB}{item_id}")]]
        )

    await send_reply(callback, "📸 <b>Все фото объявления</b>", markup=back_keyboard)
    #await callback.message.answer("______________________________________________________"
    # data сейчас: id (category|subcategory|item), name (category|subcategory)


def _item_details_text(
        item,
        category_name: str,
        subcategory_name: str
) -> str:
    return (
        f"📦 <b>{item.title}</b>\n\n"
        f"📝 <b>Описание:</b>\n{item.description}\n\n"
        f"🏷️ <b>Категория:</b> {category_name} > {subcategory_name}\n"
        f"💰 <b>Цена:</b> {format_price(item.price)} ₽/день\n"
        f"🕒 <b>Минимальный срок аренды:</b> {item.min_rental_period} {format_days(item.min_rental_period)}\n"
        f"🔐 <b>Залог:</b> {f'{format_price(item.deposit)} ₽' if item.deposit else 'Без залога'}\n"
        f"📍 <b>Местоположение:</b> {item.location}\n"
        #f"👤 <b>Владелец:</b> {item.user_id}\n"
        #f"⭐ <b>Рейтинг:</b> ... ({item.views_count} отзывов)\n"
        f"✅ <b>Доступность:</b> {'Доступно для аренды' if item.is_available else 'Временно недоступно'}\n\n"
    )

# ─────────────────────────────────────────────────helpers──────────────────────────────────────────────────────────────

async def _resolve_category(callback: CallbackQuery, category_service: CategoryService, category_id: int | None):

    if category_id is None:
        await send_or_edit(callback, "⚠️ Не удалось распознать категорию.")
        return None

    try:
        category = await category_service.get_category(category_id)
    except ServiceError:
        await send_or_edit(callback, "⚠️ Не удалось загрузить категорию. Попробуйте позже.")
        return None

    if not category:
        await callback.answer("⚠️ Категория не найдена", show_alert=True)
        return None # await show_categories(callback, category_service)

    return category

async def _store_selected_category(state: FSMContext, category) -> None:
    await state.update_data(
        selected_category_id=category.id,
        selected_category_name=category.name,
        selected_subcategory_id=None,
        selected_subcategory_name=None,
    )


async def _load_subcategories_or_notify(
    callback: CallbackQuery,
    category_service: CategoryService,
    category_id: int | None,
    category_name: str
):
    if category_id is None:
        await send_or_edit(callback, "⚠️ Не удалось распознать категорию.")
        return None

    try:
        subcategories = await category_service.list_subcategories(category_id)
    except ServiceError:
        await send_or_edit(callback, "⚠️ Не удалось загрузить подкатегории. Попробуйте позже.")
        return None

    if not subcategories:
        text = f"⚠️ В категории <b>{category_name}</b> пока нет подкатегорий."
        await send_or_edit(callback, text)
        return None

    return subcategories