from aiogram.types import CallbackQuery, Message
from collections.abc import Awaitable, Callable

from services.user_service import UserService

from status.user_status import AccountStatus
from keyboards.admin_kb import get_admin_users_menu_keyboard, get_admin_user_card_keyboard
from utils.functions import send_or_edit


def format_user_card(user) -> str:
    """Сформировать карточку пользователя для админки"""
    username = user.username
    status = user.account_status

    lines = [
        "👥 <b>Пользователь</b>",
        f"• user_id: <b>{user.id}</b>",
        f"• username: @{username}" if username else "• username: —",
        f"• account_status: <b>{status.value}</b>",
    ]

    if status == AccountStatus.BANNED:
        banned_at = user.banned_at
        banned_by_admin_id = user.banned_by_admin_id
        ban_reason = user.ban_reason

        if banned_at:
            lines.append(f"• banned_at: {banned_at}")
        if banned_by_admin_id:
            lines.append(f"• banned_by_admin_id: {banned_by_admin_id}")
        if ban_reason:
            lines.append(f"• ban_reason: {ban_reason}")

    return "\n".join(lines)


def parse_admin_user_id(raw_text: str | None) -> int | None:
    """Распарсить user_id из текстового ввода"""
    if not raw_text:
        return None

    try:
        return int(raw_text.strip())
    except ValueError:
        return None


async def get_admin_user_id_or_alert(callback: CallbackQuery) -> int | None:
    """Получить user_id из callback data или показать alert"""
    try:
        return int((callback.data or "").split(":")[-1])
    except (ValueError, IndexError):
        await callback.answer("Некорректный user-ID", show_alert=True)
        return None


async def show_user_card(event: Message | CallbackQuery, user_service: UserService, user_id: int) -> None:
    """Показать карточку пользователя в админке"""

    user = await user_service.get_by_id(user_id)
    if not user:
        await send_or_edit(event, f"❌ Пользователь #{user_id} не найден.", None)
        return

    await send_or_edit(
        event,
        format_user_card(user),
        get_admin_user_card_keyboard(user.id, user.account_status)
    )


async def apply_user_action_and_show_card(
    event: Message | CallbackQuery,
    user_service: UserService,
    user_id: int,
    action_call: Callable[[], Awaitable[object | None]],
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

    await show_user_card(event, user_service, user_id)