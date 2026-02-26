import logging

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from keyboards.admin_kb import get_admin_users_menu_keyboard, get_admin_user_card_keyboard
from services.user_service import UserService
from states.admin import AdminStates
from utils.functions import send_or_edit
#from utils.user_status import ACTIVE, BANNED

logger = logging.getLogger(__name__)
admin_users_router = Router()

"""
"Найти по user_id" - "admin:users:find"
"🚫 Ban" - f"admin:users:ban:{user_id}"
"✅ Unban" - f"admin:users:unban:{user_id}"
"🔄 Обновить" - f"admin:users:view:{user_id}"
"""

def _format_user_card(user) -> str:
    username = getattr(user, "username", None)
    status = getattr(user, "account_status", ACTIVE)

    lines = [
        "👥 <b>Пользователь</b>",
        f"• user_id: <b>{user.id}</b>",
        f"• username: @{username}" if username else "• username: —",
        f"• account_status: <b>{status}</b>",
    ]

    if status == BANNED:
        banned_at = getattr(user, "banned_at", None)
        banned_by_admin_id = getattr(user, "banned_by_admin_id", None)
        ban_reason = getattr(user, "ban_reason", None)

        if banned_at:
            lines.append(f"• banned_at: {banned_at}")
        if banned_by_admin_id:
            lines.append(f"• banned_by_admin_id: {banned_by_admin_id}")
        if ban_reason:
            lines.append(f"• ban_reason: {ban_reason}")

    return "\n".join(lines)

async def _show_user_card(event: Message | CallbackQuery, user_service: UserService, user_id: int) -> None:
    user = await user_service.get_by_id(user_id)
    if not user:
        await send_or_edit(event, f"❌ Пользователь #{user_id} не найден.", None)
        return

    text = _format_user_card(user)
    kb = get_admin_user_card_keyboard(user.id, user.account_status)
    await send_or_edit(event, text, kb)


@admin_users_router.callback_query(F.data == "admin:users")
async def admin_users_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await send_or_edit(callback, "👥 <b>Управление пользователями</b>", get_admin_users_menu_keyboard())
    await callback.answer()


@admin_users_router.callback_query(F.data == "admin:users:find")
async def admin_users_find(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminStates.waiting_user_id)
    await send_or_edit(callback, "Введите user_id (число):", None)
    await callback.answer()


@admin_users_router.message(AdminStates.waiting_user_id)
async def admin_users_find_message(message: Message, state: FSMContext, user_service: UserService,
) -> None:
    try:
        user_id = int(message.text.strip())
    except Exception:
        await send_or_edit(message, "Введите корректный user_id (число):", None)
        return

    await state.clear()
    await _show_user_card(message, user_service, user_id)


@admin_users_router.callback_query(F.data.startswith("admin:users:view:"))
async def admin_users_view(callback: CallbackQuery, user_service: UserService) -> None:
    try:
        user_id = int(callback.data.split(":")[-1])
    except Exception:
        await callback.answer("Некорректный ID", show_alert=True)
        return

    await _show_user_card(callback, user_service, user_id)
    await callback.answer()


@admin_users_router.callback_query(F.data.startswith("admin:users:ban:"))
async def admin_users_ban_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        user_id = int(callback.data.split(":")[-1])
    except Exception:
        await callback.answer("Некорректный ID", show_alert=True)
        return

    await state.set_state(AdminStates.waiting_user_ban_reason)
    await state.update_data(target_user_id=user_id)
    await send_or_edit(callback, "Введите причину бана одним сообщением:", None)
    await callback.answer()


@admin_users_router.message(AdminStates.waiting_user_ban_reason)
async def admin_users_ban_apply(message: Message, state: FSMContext, user_service: UserService, user) -> None:
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

    try:
        updated = await user_service.ban_user(user_id, admin_user_id=user.id, reason=reason)
        #updated = await user_service.ban_user(user_id, admin_user_id=message.from_user.id, reason=reason)
    except ValueError as exc:
        await state.clear()
        await send_or_edit(message, f"❌ {exc}", None)
        return

    await state.clear()
    if not updated:
        await send_or_edit(message, f"❌ Пользователь #{user_id} не найден.", None)
        return

    await _show_user_card(message, user_service, user_id)


@admin_users_router.callback_query(F.data.startswith("admin:users:unban:"))
async def admin_users_unban(callback: CallbackQuery, user_service: UserService) -> None:
    try:
        user_id = int(callback.data.split(":")[-1])
    except Exception:
        await callback.answer("Некорректный ID", show_alert=True)
        return

    try:
        updated = await user_service.unban_user(user_id)
    except ValueError as exc:
        await send_or_edit(callback, f"❌ {exc}", None)
        await callback.answer()
        return

    if not updated:
        await send_or_edit(callback, f"❌ Пользователь #{user_id} не найден.", None)
        await callback.answer()
        return

    await _show_user_card(callback, user_service, user_id)
    await callback.answer()

