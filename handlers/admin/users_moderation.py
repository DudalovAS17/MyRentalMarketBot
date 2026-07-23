from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from collections.abc import Awaitable, Callable

from services.user_service import UserService
from services.admin_service import AdminActionService
from .admin_helpers.parse import get_admin_user_id_or_alert, parse_admin_user_id
from .admin_helpers.show import show_user_card
from .admin_helpers.keyboard import get_admin_users_menu_keyboard

from states.admin import AdminStates
from status.admin_status import AdminActionType, AdminEntityType
from utils.functions import send_or_edit
from utils.callbacks import ADMIN_USERS_MOD, ADMIN_USERS_MOD_VIEW, ADMIN_USERS_MOD_FIND, ADMIN_USERS_MOD_BAN, ADMIN_USERS_MOD_UNBAN

admin_users_router = Router()

# ***** кнопка админки "Наши клиенты" *****

# ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
@admin_users_router.callback_query(F.data == ADMIN_USERS_MOD)
async def admin_users_menu(callback: CallbackQuery, state: FSMContext) -> None:
    """Показать меню управления пользователями"""
    await callback.answer()

    await state.clear()
    await send_or_edit(callback, "👥 <b>Управление пользователями</b>", get_admin_users_menu_keyboard())

@admin_users_router.callback_query(F.data.startswith(ADMIN_USERS_MOD_VIEW))
async def admin_users_view(callback: CallbackQuery, user_service: UserService) -> None:
    """Показать карточку пользователя"""
    await callback.answer()

    user_id = await get_admin_user_id_or_alert(callback)
    if user_id is None:
        return

    await show_user_card(callback, user_service, user_id)


# ────────────────────────────────────── Поиск по клиента по id ────────────────────────────────────────────────────────
@admin_users_router.callback_query(F.data == ADMIN_USERS_MOD_FIND)
async def admin_users_find(callback: CallbackQuery, state: FSMContext) -> None:
    """Запросить id для поиска клиента"""
    await callback.answer()

    await state.set_state(AdminStates.waiting_user_id)
    await send_or_edit(callback, "Введите user_id (число):", None)

@admin_users_router.message(AdminStates.waiting_user_id)
async def admin_users_find_message(message: Message, state: FSMContext, user_service: UserService) -> None:
    """Обработать введённый id и показать карточку пользователя"""

    user_id = parse_admin_user_id(message.text)
    if user_id is None:
        await send_or_edit(message, "Введите корректный user_id (число):", None)
        return

    await state.clear()
    await show_user_card(message, user_service, user_id)


# ──────────────────────────────────────── Логика бана ─────────────────────────────────────────────────────────────────
@admin_users_router.callback_query(F.data.startswith(ADMIN_USERS_MOD_BAN))
async def admin_users_ban_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    """Запросить причину бана клиента"""
    await callback.answer()

    user_id = await get_admin_user_id_or_alert(callback)
    if user_id is None:
        return

    await state.set_state(AdminStates.waiting_user_ban_reason)
    await state.update_data(target_user_id=user_id)
    await send_or_edit(callback, "Введите причину бана одним сообщением:", None)

@admin_users_router.message(AdminStates.waiting_user_ban_reason)
async def admin_users_ban_apply(message: Message, state: FSMContext, user_service: UserService, admin_service: AdminActionService, admin) -> None:
    """Применить бан клиента с причиной"""
    data = await state.get_data()

    user_id = data.get("target_user_id")
    if not user_id:
        await state.clear()
        await send_or_edit(message, "Не удалось определить клиента. Повторите попытку.", None)
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
        action_call=lambda: user_service.ban_user(user_id=user_id, reason=reason, admin_telegram_id=message.from_user.id),
        audit_call=lambda: admin_service.log_action(
            admin_tg_id=message.from_user.id, admin_id=admin.id,
            action_type=AdminActionType.BAN_USER,
            entity_type=AdminEntityType.USER, entity_id=user_id, note=reason
        )
    )


# ──────────────────────────────────────── Логика разбана ──────────────────────────────────────────────────────────────
@admin_users_router.callback_query(F.data.startswith(ADMIN_USERS_MOD_UNBAN))
async def admin_users_unban(callback: CallbackQuery, user_service: UserService, admin_service: AdminActionService, admin) -> None:
    """Разбанить пользователя"""
    await callback.answer()

    user_id = await get_admin_user_id_or_alert(callback)
    if user_id is None:
        return

    await apply_user_action_and_show_card(
        event=callback,
        user_service=user_service,
        user_id=user_id,
        action_call=lambda: user_service.unban_user(user_id, admin_telegram_id=callback.from_user.id),
        audit_call=lambda: admin_service.log_action(
            admin_tg_id=callback.from_user.id, admin_id=admin.id,
            action_type=AdminActionType.UNBAN_USER,
            entity_type=AdminEntityType.USER, entity_id=user_id
        ),
    )


# ──────────────────────────────────────────────── helpers ─────────────────────────────────────────────────────────────
async def apply_user_action_and_show_card(
    event: Message | CallbackQuery,
    user_service: UserService,
    user_id: int,
    action_call: Callable[[], Awaitable[object | None]],
    audit_call: Callable[[], Awaitable[object]] | None = None,
) -> None:
    """Выполнить admin-action над пользователем и перерисовать карточку"""
    try:
        updated = await action_call()
    except ValueError as exc:
        await send_or_edit(event, f"❌ {exc}", None)
        return

    if not updated:
        await send_or_edit(event, f"❌ Пользователь #{user_id} не найден.", None)
        return

    if audit_call is not None:
        await audit_call()

    await show_user_card(event, user_service, user_id)