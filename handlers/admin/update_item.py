from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from handlers.admin import create_helpers as ch
from services.item_service import ItemService
#from keyboards.item_kb import build_edit_item_keyboard
from utils.functions import send_or_edit
from utils.validators import parse_callback
from utils.callbacks import ADMIN_EDIT_ITEM_CB

admin_update_item_router = Router()

# ПОКА НЕРАБОЧАЯ ЛОГИКА!

# ────────────────────────────────────────── Редактирования ✏️ товара ──────────────────────────────────────────────
@admin_update_item_router.callback_query(F.data.startswith(ADMIN_EDIT_ITEM_CB))
async def start_process_edit_item(callback: CallbackQuery, state: FSMContext, item_service: ItemService) -> None:
    """📝 Начало процесса редактирования товара"""
    await callback.answer()

    item = await ch.load_entity_or_notify(
        callback, item_service.get_item_by_id, parse_callback(callback.data, ADMIN_EDIT_ITEM_CB),
        invalid_id_text=ch.not_item_id, load_error_text=ch.serv_err_item, not_found_text=ch.not_item
    )
    if item is None:
        return

    # Сохраняем данные для редактирования
    await ch.init_edit_item_context(state, item)

    await send_or_edit(
        callback,
        ch.edit_item_start_text(item),
        #markup=build_edit_item_keyboard(item.id),
        parse_mode="HTML"
    )