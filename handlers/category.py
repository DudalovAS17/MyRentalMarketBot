import logging
#from typing import Union

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from aiogram.fsm.context import FSMContext
from typing import Union

from utils.functions import format_price
from keyboards.main_kb import build_category_keyboard

from services.item_service import ItemService
from services.category_service import CategoryService
from services.photo_service import PhotoService
from services.rental_service import RentalService

#from states.item import ItemCreateStates

logger = logging.getLogger(__name__)
category_router = Router()

# Константы callback-данных
CAT_CB_PREFIX = "cat:"
SUBCAT_CB_PREFIX = "subcat:"
SEARCH_CITY_CB = "search_by_city"
SEARCH_FILTERS_CB = "search_filters"
BACK_TO_MENU_CB = "back_to_main_menu"
ALL_CATEGORY_CB = "all_cat"
BACK_TO_CAT = "back_to_categories"

async def show_categories(
        event: Union[Message, CallbackQuery],
        #state: FSMContext,
        category_service: CategoryService,
) -> None:
    """Показывает список категорий для выбора. Сценарий поиска («🔍 Арендовать») """
    logger.info(f"Вызвана функция show_categories")

    # ⚙️ Получаем категории
    try:
        categories = await category_service.list_main_categories() or []
    except Exception as e:
        logger.error("show_categories(): не удалось получить категории: %s", e, exc_info=True)
        categories = []

    # 🧱 Формируем клавиатуру
    keyboard = build_category_keyboard(
        categories,
        prefix=CAT_CB_PREFIX,
        extra_buttons=[ # Для сценария поиска — оставим «Поиск по городу» и «Фильтры»
            [InlineKeyboardButton(text="🏙️ Поиск по городу", callback_data=SEARCH_CITY_CB)],
            [InlineKeyboardButton(text="⚙️ Фильтры", callback_data=SEARCH_FILTERS_CB)],
            [InlineKeyboardButton(text="🔙 Назад в меню", callback_data=BACK_TO_MENU_CB)]
        ]
    )

    message_text = "🔍 <b>Арендовать</b>\n\nВыберите категорию:"

    await event.answer(message_text, reply_markup=keyboard, parse_mode="HTML")


@category_router.callback_query(F.data.startswith(CAT_CB_PREFIX))
async def show_subcategories(callback: CallbackQuery,
    category_service: CategoryService): # state: FSMContext,
    """Показывает список подкатегорий выбранной категории"""

    await callback.answer()
    try:
        category_id = int(callback.data.split(":")[1])
        logger.info(f"Вызвана функция show_subcategories с category_id={category_id}")
    except (IndexError, ValueError):
        await callback.message.answer("⚠️ Не удалось распознать категорию.")
        return

    category = await category_service.get_category(category_id)
    if not category:
        await callback.answer("⚠️ Категория не найдена", show_alert=True)
        return

    subcategories = await category_service.list_subcategories(category_id)
    if not subcategories:
        await callback.message.edit_text(
                f"⚠️ В категории <b>{category.name}</b> пока нет подкатегорий."
            )
        return

    keyboard = build_category_keyboard(
        subcategories,
        prefix=SUBCAT_CB_PREFIX,
        extra_buttons=[
            [InlineKeyboardButton(text=f"📋 Все в категории {category.name}",
                                  callback_data=f"{ALL_CATEGORY_CB}:{category.id}")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data=BACK_TO_CAT)]
        ]
    )
    # Идея: Добавляем кнопки для каждой подкатегории

    #data = await state.get_data()

    text = (f"🔍 <b>Поиск в категории {category.name}</b>\n\n"
            f"Выберите подкатегорию:")

    # Отправляем или обновляем сообщение с клавиатурой
    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    except Exception as e:
        logger.warning("Не удалось отредактировать сообщение подкатегорий: %s", e)
        await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@category_router.callback_query(F.data.startswith(SUBCAT_CB_PREFIX))
async def show_items_in_subcategory(
    callback: CallbackQuery,
    state: FSMContext,
    item_service: ItemService,
    category_service: CategoryService,
    #limit: int = 10
):
    """Показывает список объявлений в выбранной подкатегории
        limit: ограничение по количеству объявлений"""

    try:
        subcategory_id = int(callback.data.split(":")[1])
        logger.info(f"Вызвана функция show_items_in_subcategory с category_id={subcategory_id}")
    except (IndexError, ValueError):
        await callback.message.answer("⚠️ Не удалось распознать категорию.")
        return

    subcategory = await category_service.get_category(subcategory_id)
    if not subcategory:
        await callback.answer("⚠️ Подкатегория не найдена", show_alert=True)
        return

    # Сохраняем в контекст выбранную подкатегорию
    await state.update_data(
        selected_subcategory_id=subcategory.id,
        selected_subcategory_name=subcategory.name
    )

    # получаем список объявлений по подкатегории
    items = await item_service.list_by_subcategory(subcategory_id) # , limit=limit

    # Если пришёл callback — убираем «часики»
    await callback.answer()

    # Узнаём режим: поиск или создание объявления
    #data = await state.get_data()
    #for_search = data.get("for_search", True)

    if not items:
        message_text = f"⚠️ В подкатегории <b>{subcategory.name}</b> пока нет объявлений."
        await callback.message.edit_text(message_text, parse_mode="HTML")
        return

    # строим клавиатуру объявлений
    keyboard_rows = []
    for item in items:
        btn_text = f"{item.title} — {item.price} ₽/день"
        btn_cb = f"show_item_details:{item.id}" # было show_item!!!!!!!!
        keyboard_rows.append([InlineKeyboardButton(text=btn_text, callback_data=btn_cb)])

    # Кнопка назад
    keyboard_rows.append([
        InlineKeyboardButton(text="🔙 Назад", callback_data=f"cat:{subcategory.parent_id}")
    ])

    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)

    message_text = f"📋 Объявления в подкатегории <b>{subcategory.name}</b>:"

    try:
        await callback.message.edit_text(message_text, reply_markup=reply_markup, parse_mode="HTML")
    except Exception as e:
        logger.warning("Не удалось отредактировать сообщение списка объявлений: %s", e)
        await callback.message.answer(message_text, reply_markup=reply_markup, parse_mode="HTML")


@category_router.callback_query(F.data.startswith("show_item_details:"))
async def show_item_details_in_subcategory(
    callback: CallbackQuery,
    state: FSMContext,
    item_service: ItemService,
    category_service: CategoryService,
    photo_service: PhotoService,
    rental_service: RentalService,
) -> None:
    """Просмотр всех деталей конкретного объявления"""
    await callback.answer()

    try:
        item_id = int(callback.data.split(":")[1])
        logger.info(f"Вызвана функция show_item_details_in_subcategory с item_id={item_id}")
    except (IndexError, ValueError):
        await callback.message.answer("⚠️ Не удалось распознать категорию.")
        return

    # Получаем объявление
    item = await item_service.get_item_by_id(item_id)
    if not item:
        await callback.message.edit_text("❌ Объявление не найдено.")
        await show_categories(callback, category_service) # state,

    data = await state.get_data()
    category_name = data.get("selected_category_name", "Неизвестно")
    # category_name = data.get("selected_category_name") or (await category_service.get_category(item.category_id)).name
    subcategory_name = data.get("selected_subcategory_name", "Неизвестно")

    # Формируем детальную информацию
    item_details = (
        f"📦 <b>{item.title}</b>\n\n"
        f"📝 <b>Описание:</b>\n{item.description}\n\n"
        f"🏷️ <b>Категория:</b> {category_name} > {subcategory_name}\n"
        f"💰 <b>Цена:</b> {format_price(item.price)} ₽/день\n"
        f"🕒 <b>Минимальный срок аренды:</b> {item.min_rental_period} "
        f"{'день' if item.min_rental_period == 1 else 'дня' if 1 < item.min_rental_period < 5 else 'дней'}\n"
        #f"🔐 <b>Залог:</b> {format_price(item.deposit) if item.deposit else 'Без залога'} ₽\n"
        f"🔐 <b>Залог:</b> {f'{format_price(item.deposit)} ₽' if item.deposit else 'Без залога'}\n"
        f"📍 <b>Местоположение:</b> {item.location}\n"
        f"👤 <b>Владелец:</b> {item.user_id}\n"
        #f"⭐ <b>Рейтинг:</b> ... ({item.views_count} отзывов)\n"
        f"✅ <b>Доступность:</b> {'Доступно для аренды' if item.is_available else 'Временно недоступно'}\n\n"
    )

    # Клавиатура
    keyboard = []
    #if item.is_available:
    open_rental = await rental_service.get_open_rental_for_item(item_id)
    if open_rental:
        end_str = open_rental.end_date.strftime("%d.%m.%Y") if open_rental.end_date else None
        # end_str = getattr(open_rental, "end_date", None)
        button_text = f"⛔ Занято (до {end_str})" if end_str else "⛔ Занято"
        keyboard.append([InlineKeyboardButton(text=button_text, callback_data="noop")])
    else:
        keyboard.append([InlineKeyboardButton(text="🤝 Арендовать", callback_data=f"rent_item:{item_id}")])
    keyboard.append([InlineKeyboardButton(text="📸 Показать все фото", callback_data=f"show_all_photos:{item_id}")])
    keyboard.append([InlineKeyboardButton(text="💬 Написать владельцу", callback_data=f"message_owner:{item_id}")])
    keyboard.append([InlineKeyboardButton(text="⭐ Отзывы", callback_data=f"reviews:{item_id}")])
    keyboard.append([InlineKeyboardButton(text="🔙 Назад к списку", callback_data=BACK_TO_CAT)])

    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

    # ======== ФОТО =========
    photos = await photo_service.get_photos(item_id)

    # удаляем предыдущее сообщение
    try:
        await callback.message.delete()
    except:
        pass

    if photos:
        # отправляем главное фото
        await callback.message.answer_photo(
            photo=photos[0].telegram_file_id,
            caption=item_details,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
    else:
        # без фото
        await callback.message.answer( # edit_text
            item_details,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )


@category_router.callback_query(F.data.startswith("show_all_photos:"))
async def show_all_photos(
    callback: CallbackQuery,
    state: FSMContext,
    photo_service: PhotoService
):
    """Показать все фотографии объявления (альбомом)."""
    await callback.answer()

    # Если уже показывали — просто игнорируем повтор
    #data = await state.get_data()
    #if data.get("album_shown"):
    #    await callback.message.answer("📸 Фото уже показаны выше.")
    #    return

    item_id = int(callback.data.split(":")[1])

    photos = await photo_service.get_photos(item_id)
    if not photos:
        await callback.message.answer("📭 У этого объявления нет фотографий.")
        return

    media = []
    for p in photos:
        media.append(
            InputMediaPhoto(media=p.telegram_file_id)
        )

    # Телега требует удалить старое сообщение перед media_group
    try:
        await callback.message.delete()
    except:
        pass

    # отправляем альбом
    await callback.message.answer_media_group(media)

    # отправляем кнопку назад
    await callback.message.answer(
        "____________________________________________________________",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data=f"show_item_details:{item_id}")]
            ]
        )
    )

# ============================ поиски (не реализовано) =============================================

@category_router.callback_query(F.data == "search_by_name")
async def search_by_name(callback: CallbackQuery, state: FSMContext, category_service: CategoryService):
    await callback.answer("Выбран поиск по названию")

    search_text = (
        "🔎 <b>Поиск по названию</b>\n\n"
        "Введите название вещи, которую хотите найти.\n"
        "Например: 'палатка', 'велосипед', 'дрель'...\n\n"
        "Вы можете искать по любым ключевым словам."
    )

    keyboard = [[InlineKeyboardButton(text="🔙 Назад к категориям", callback_data=BACK_TO_CAT)]]
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

    await callback.message.edit_text(search_text, reply_markup=reply_markup, parse_mode="Markdown")
    await callback.answer("Функция поиска по названию в разработке! 🛠️")

    return await show_categories(callback, category_service)

# process_category_selection
"""
async def process_category_selection(update: Update, context: CallbackContext) -> Optional[int]:
    ""
    Обрабатывает выбор категории или подкатегории.

    Args:
        update: Объект Update от Telegram
        context: Контекст бота

    Returns:
        Optional[int]: Следующее состояние диалога или None
    ""
    # Добавляем импорт здесь
    from handlers.base import show_main_menu
    query = update.callback_query
    await query.answer()

    callback_data = query.data

    # Логируем полученный запрос
    logger.info(f"Получен callback_data: {callback_data}")


    if callback_data == "search_by_name":
        # Выбран поиск по названию
        await query.answer("Выбран поиск по названию")

        search_text = (
            "🔎 *Поиск по названию*\n\n"
            "Введите название вещи, которую хотите найти.\n"
            "Например: 'палатка', 'велосипед', 'дрель' и т.д.\n\n"
            "Вы можете искать по любым ключевым словам."
        )

        # Клавиатура для отмены поиска
        keyboard = [[InlineKeyboardButton("🔙 Назад к категориям", callback_data=f"{BACK_CB}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            search_text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

        # Здесь будет переход к состоянию SEARCH_BY_NAME
        # Сейчас возвращаем к основному списку категорий
        await query.answer("Функция поиска по названию в разработке! 🛠️")
        return await show_categories(update, context, True)

    elif callback_data == "search_by_city":
        # Выбран поиск по городу
        return await process_search_by_city(update, context)

    elif callback_data == "search_filters":
        # Выбраны фильтры поиска
        return await process_search_filters(update, context)

    elif callback_data == ALL_CATEGORY_CB:
        # Выбраны все категории для поиска
        context.user_data["selected_category_id"] = None
        context.user_data["selected_subcategory_id"] = None

        # Переходим к поиску по всем категориям
        await query.answer("Выбраны все категории для поиска")
        return await search_in_all_categories(update, context)


    elif callback_data == BACK_CB:
        # Если выбрана кнопка "Назад"
        if "selected_category_id" in context.user_data:
            # Возвращаемся к списку категорий
            context.user_data.pop("selected_category_id", None)
            context.user_data.pop("selected_category_name", None)
            return await show_categories(update, context, context.user_data.get("for_search", True))
        else:
            # Возвращаемся в главное меню
            return await show_main_menu(update, context)

    # Обработка выбора объявления для просмотра
    elif callback_data.startswith("item:"):
        item_id = int(query.data.split(":")[1])
        return await show_item_details_in_subcategory(update, context, item_id)

    # Обработка подтверждения публикации объявления
    elif callback_data in ["publish_item", "edit_item"]:
        return await process_item_confirmation(update, context)

    # По умолчанию возвращаемся в главное меню
    return await show_main_menu(update, context)
"""

# !!! смотри старый хэндлер категорий

#async def search_in_all_categories

# поиска по городу и фильтров
#async def process_search_by_cit

# фильтры
#async def process_search_filters

# Поиск имени подкатегории по ID              *Удалено*
#def get_subcategory_name_by_id(category_id, subcategory_id):