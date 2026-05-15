from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext


from services.user_service import UserService
from .admin_helpers.file_users import show_user_card, get_admin_user_id_or_alert, parse_admin_user_id, apply_user_action_and_show_card

from keyboards.admin_kb import get_admin_users_menu_keyboard
from states.admin import AdminStates
from utils.functions import send_or_edit


admin_users_router = Router()

"""
"Найти по user_id" - "admin:users:find"
"🚫 Ban" - f"admin:users:ban:{user_id}"
"✅ Unban" - f"admin:users:unban:{user_id}"
"🔄 Обновить" - f"admin:users:view:{user_id}"
"""

# ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
@admin_users_router.callback_query(F.data == "admin:users")
async def admin_users_menu(callback: CallbackQuery, state: FSMContext) -> None:
    """Показать меню управления пользователями"""
    await callback.answer()

    await state.clear()
    await send_or_edit(callback, "👥 <b>Управление пользователями</b>", get_admin_users_menu_keyboard())


@admin_users_router.callback_query(F.data.startswith("admin:users:view:"))
async def admin_users_view(callback: CallbackQuery, user_service: UserService) -> None:
    """Показать карточку пользователя по callback-кнопке"""
    await callback.answer()

    user_id = await get_admin_user_id_or_alert(callback)
    if user_id is None:
        return

    await show_user_card(callback, user_service, user_id)


# ──────────────────────────────────────── поиск по user-id ────────────────────────────────────────────────────────────
@admin_users_router.callback_query(F.data == "admin:users:find")
async def admin_users_find(callback: CallbackQuery, state: FSMContext) -> None:
    """Запросить user_id для поиска пользователя"""
    await callback.answer()

    await state.set_state(AdminStates.waiting_user_id)
    await send_or_edit(callback, "Введите user_id (число):", None)

@admin_users_router.message(AdminStates.waiting_user_id)
async def admin_users_find_message(message: Message, state: FSMContext, user_service: UserService) -> None:
    """Обработать введённый user_id и показать карточку пользователя"""

    user_id = parse_admin_user_id(message.text)
    if user_id is None:
        await send_or_edit(message, "Введите корректный user_id (число):", None)
        return

    await state.clear()
    await show_user_card(message, user_service, user_id)


# ───────────────────────────────────── причина бана по user-id ────────────────────────────────────────────────────────
@admin_users_router.callback_query(F.data.startswith("admin:users:ban:"))
async def admin_users_ban_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    """Запросить причину бана пользователя"""
    await callback.answer()

    user_id = await get_admin_user_id_or_alert(callback)
    if user_id is None:
        return

    await state.set_state(AdminStates.waiting_user_ban_reason)
    await state.update_data(target_user_id=user_id)
    await send_or_edit(callback, "Введите причину бана одним сообщением:", None)


@admin_users_router.message(AdminStates.waiting_user_ban_reason)
async def admin_users_ban_apply(message: Message, state: FSMContext, user_service: UserService, user) -> None:
    """Применить бан пользователя с причиной"""
    data = await state.get_data()

    user_id = data.get("target_user_id")
    if not user_id:
        await state.clear()
        await send_or_edit(message, "Не удалось определить пользователя. Повторите попытку.", None)
        return

    reason = (message.text or "").strip()
    if not reason:
        await send_or_edit(message, "Укажите причину бана текстом.", None)
        return

    await state.clear()

    await apply_user_action_and_show_card(
        event=message,
        user_service=user_service,
        user_id=user_id,
        action_call=lambda: user_service.ban_user(user_id=user_id, admin_user_id=user.id, reason=reason),
    ) # admin_user_id=message.from_user.id


# ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
@admin_users_router.callback_query(F.data.startswith("admin:users:unban:"))
async def admin_users_unban(callback: CallbackQuery, user_service: UserService) -> None:
    """Разбанить пользователя"""
    await callback.answer()

    user_id = await get_admin_user_id_or_alert(callback)
    if user_id is None:
        return

    await apply_user_action_and_show_card(
        event=callback,
        user_service=user_service,
        user_id=user_id,
        action_call=lambda: user_service.unban_user(user_id)
    )