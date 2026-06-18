from aiogram import F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from .router import items_router

from ..admin import create_helpers as ch
from services.item_service import ItemService
from services.category_service import CategoryService
#from handlers.entries.item_entry import show_my_items
from keyboards.item_kb import build_my_item_details_keyboard
from utils.functions import send_or_edit
from utils.validators import parse_callback
from utils.callbacks import SHOW_ITEM_CB, MY_ITEMS_PREFIX


#@items_router.message(F.text == "📦 Мои объявления")
#@items_router.callback_query(F.data == MY_ITEMS_PREFIX)
#show_my_items_entry - Показывает список объявлений пользователя (show_my_items)


@items_router.callback_query(F.data.startswith(SHOW_ITEM_CB))
async def show_item_details(
        callback: CallbackQuery,
        state: FSMContext,
        item_service: ItemService,
        category_service: CategoryService
) -> None:
    """Показывает детали товара"""
    await callback.answer()

    item = await ch.load_item(
        callback, item_service.get_item_by_id, parse_callback(callback.data, SHOW_ITEM_CB), invalid_id_text=ch.not_item_id,
        load_error_text=ch.serv_err_item, not_found_text=ch.not_item, markup_back=ch.build_back_to_my_items_keyboard()
    )
    if item is None:
        return

    await ch.store_selected_item(state, item.id)

    category_name, subcategory_name = await ch.load_item_category_context(
        category_service=category_service, item=item)

    await send_or_edit(
        callback,
        ch.item_details_text(item, category_name, subcategory_name),
        markup=build_my_item_details_keyboard(item)
    )