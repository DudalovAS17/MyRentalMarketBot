import logging
from aiogram import F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from .router import items_router

from services.item_service import ItemService
from services.category_service import CategoryService
from utils.functions import format_price
from keyboards.item_kb import build_my_items_keyboard, build_my_item_details_keyboard
from utils.functions import send_or_edit, send_reply, format_days
from utils.errors import ServiceError

logger = logging.getLogger(__name__)

SHOW_ITEM_CB = "show_item:"
MY_ITEMS_PREFIX = "my_items"


@items_router.message(F.text == "📦 Мои объявления")
@items_router.callback_query(F.data == MY_ITEMS_PREFIX)
async def show_my_items(event: Message | CallbackQuery, item_service: ItemService, user) -> None: # state: FSMContext,
    """Показывает список объявлений пользователя"""

    if isinstance(event, CallbackQuery):
        await event.answer()

    try:
        items = await item_service.list_by_user(user.id)
    except ServiceError:
        # Ожидаемая бизнес-ошибка: коротко пользователю
        await send_reply(event, "⚠️ Не удалось загрузить ваши объявления. Попробуйте позже.")
        return # await show_main_menu()

    items = items or []

    if not items:
        message_text = (
            "📦 <b>Мои объявления</b>\n\n"
            "У вас пока нет активных объявлений.\n"
            "Создайте новое объявление, чтобы сдать вещи в аренду!"
        )
    else:
        message_text = (
            "📦 <b>Мои объявления</b>\n\n"
            f"У вас {len(items)} {_get_items_count_str(len(items))}.\n"
            "Выберите объявление для просмотра или редактирования:"
        )

    markup = build_my_items_keyboard(items)

    await send_or_edit(event, message_text, markup=markup)
    return


@items_router.callback_query(F.data.startswith(SHOW_ITEM_CB))
async def show_item_details(
        callback: CallbackQuery,
        state: FSMContext,
        item_service: ItemService,
        category_service: CategoryService
) -> None:
    """Показывает детали объявления"""

    await callback.answer()

    try:
        item_id = int(callback.data.split(":")[1]) # .split(":", 1)
    except (IndexError, ValueError):
        await send_or_edit(callback, "⚠️ Не удалось распознать объявление.")
        return # show_my_items() ???

    await state.update_data(selected_item_id=item_id)

    try:
        item = await item_service.get_item_by_id(item_id)
    except ServiceError:
        await send_or_edit(callback, "⚠️ Не удалось загрузить объявление. Попробуйте позже.")
        return # show_my_items() ???

    if not item:
        markup = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад (к моим объявлениям)", callback_data=MY_ITEMS_PREFIX)]]
        )
        await send_or_edit(callback, "⚠️ Объявление не найдено.", markup=markup)
        return # show_my_items() ???

    # Получаем категорию и подкатегорию
    try:
        category = await category_service.get_category(item.category_id) if item.category_id else None
        subcategory = await category_service.get_category(item.subcategory_id) if item.subcategory_id else None
    except ServiceError:
        category = None
        subcategory = None

    min_days = item.min_rental_period # or 1
    item_details = (
        f"📦 <b>{item.title or 'Без названия'}</b>\n\n"
        f"📝 <b>Описание:</b>\n{item.description or 'Нет описания'}\n\n"
        f"🏷️ <b>Категория:</b> {category.name or '-'} > {subcategory.name or '-'}\n"
        f"💰 <b>Цена:</b> {format_price(item.price)} ₽/день\n"
        f"🔐 <b>Залог:</b> {f'{format_price(item.deposit)} ₽' if item.deposit else 'Без залога'}\n"
        f"🕒 <b>Минимальный срок аренды:</b> {min_days} {format_days(min_days)}\n"
        f"📍 <b>Местоположение:</b> {item.location if item.location else 'Неизвестное'} \n"
        # f"👤 <b>Владелец:</b> {item.user_id}\n"
        # f"⭐ <b>Рейтинг:</b> ... ({item.views_count} отзывов)\n"
        f"✅ <b>Доступность:</b> {'✅ Доступно для аренды' if item.is_available else '❌ Временно недоступно'}\n\n"
    )

    markup = build_my_item_details_keyboard(item)

    await send_or_edit(callback, item_details, markup=markup)
    # data сейчас: id (item), name (-)


# ==========================================================================================================
def _get_items_count_str(count: int) -> str:
    """Возвращает правильное склонение слова 'объявление'"""
    if count % 10 == 1 and count % 100 != 11:
        return "объявление"
    elif 2 <= count % 10 <= 4 and (count % 100 < 10 or count % 100 >= 20):
        return "объявления"
    else:
        return "объявлений"

def _get_days_str(days: int) -> str:
    """Возвращает правильное склонение слова 'день'"""
    if days % 10 == 1 and days % 100 != 11:
        return "день"
    elif 2 <= days % 10 <= 4 and (days % 100 < 10 or days % 100 >= 20):
        return "дня"
    else:
        return "дней"