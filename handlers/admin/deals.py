from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from services.admin_rental_service import AdminRentalService
from .admin_helpers.show import show_deals_list, show_deal_card
from .admin_helpers.parse import parse_admin_page, parse_admin_rental_id, parse_admin_rental_id_text

from states.admin import AdminStates
from utils.functions import send_or_edit

admin_deals_router = Router()

DEALS_PREFIX = "admin:deals"
DEALS_PAGE_PREFIX = "admin:deals:page:"
DEALS_VIEW_PREFIX = "admin:deals:view:"
DEALS_BY_ID_PREFIX = "admin:deals:by_id"

# ─────────────────────────────────────────────── Просмотр заявок ──────────────────────────────────────────────────────
@admin_deals_router.callback_query(F.data == DEALS_PREFIX)
async def admin_deals_list(callback: CallbackQuery, admin_rental_service: AdminRentalService) -> None:
    """Список последних заявок на аренду (страница 1)"""
    await callback.answer()

    await show_deals_list(callback, admin_rental_service, page=1)

@admin_deals_router.callback_query(F.data.startswith(DEALS_PAGE_PREFIX))
async def admin_deals_page(callback: CallbackQuery, admin_rental_service: AdminRentalService) -> None:
    """Пагинация списка заявок"""
    await callback.answer()

    page = parse_admin_page(callback.data)
    await show_deals_list(callback, admin_rental_service, page=page)

@admin_deals_router.callback_query(F.data.startswith(DEALS_VIEW_PREFIX))
async def admin_deals_view(callback: CallbackQuery, admin_rental_service: AdminRentalService) -> None: # , *, action_name: str
    """Карточка конкретной заявки"""
    rental_id = parse_admin_rental_id(callback.data)
    if rental_id is None:
        await callback.answer("Некорректный ID заявки", show_alert=True)
        return

    await callback.answer()
    await show_deal_card(callback, admin_rental_service, rental_id) # , prefix_text=f"✅ {action_name}.\n\n"

# ───────────────────────────────────────── FSM: 🔎 Открыть сделку по ID ───────────────────────────────────────────────
@admin_deals_router.callback_query(F.data == DEALS_BY_ID_PREFIX)
async def admin_deals_open_by_id(callback: CallbackQuery, state: FSMContext) -> None:
    """FSM: Просим админа ввести ID заявки"""
    await callback.answer()

    await state.set_state(AdminStates.waiting_rental_id)
    await send_or_edit(callback, "Введите ID заявки (число):", None)

@admin_deals_router.message(AdminStates.waiting_rental_id)
async def admin_deals_process_id(message: Message, state: FSMContext, admin_rental_service: AdminRentalService) -> None:
    """FSM: Обработка введенного ID заявки"""
    rental_id = parse_admin_rental_id_text(message.text)
    if rental_id is None:
        await message.answer("❌ Нужно число. Введите ID заявки:")
        return

    await state.clear()
    await show_deal_card(message, admin_rental_service, rental_id)