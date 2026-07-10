"""Проверки ролей сотрудников для админских разделов бота."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message

from schemas.admin import AdminOut
from status.admin_status import AdminRole
from texts.text_middleware import ADMIN_INACTIVE, ADMIN_ROLE_FORBIDDEN
from utils.functions import deny

ROLE_LABELS = {
    AdminRole.MANAGER: "manager",
    AdminRole.ADMIN: "admin",
    AdminRole.OWNER: "owner",
}


def normalize_admin_role(role: AdminRole | str | None) -> AdminRole | None:
    """Привести роль сотрудника к `AdminRole` или вернуть `None`, если роль неизвестна."""
    if isinstance(role, AdminRole):
        return role
    if role is None:
        return None
    try:
        return AdminRole(str(role))
    except ValueError:
        return None

def has_admin_role(admin: AdminOut | None, allowed_roles: Iterable[AdminRole]) -> bool:
    """Проверить, что активный сотрудник имеет одну из разрешённых ролей."""
    role = normalize_admin_role(getattr(admin, "role", None))
    return bool(admin and getattr(admin, "is_active", False) and role in set(allowed_roles))

async def require_admin_role(
    event: Message | CallbackQuery,
    admin: AdminOut | None,
    allowed_roles: Iterable[AdminRole],
) -> bool:
    """Проверить роль сотрудника и показать отказ, если прав недостаточно."""
    if admin is not None and not getattr(admin, "is_active", False):
        await deny(event, ADMIN_INACTIVE, alert_text="Доступ выключен", show_alert=True)
        return False

    if has_admin_role(admin, allowed_roles):
        return True

    allowed = ", ".join(ROLE_LABELS.get(role, role.value) for role in allowed_roles)
    await deny(event, ADMIN_ROLE_FORBIDDEN.format(roles=allowed), alert_text="Недостаточно прав", show_alert=True)
    return False

def can_manage_items(admin: AdminOut | None) -> bool:
    """Проверить, может ли сотрудник управлять товарами каталога."""
    return has_admin_role(admin, {AdminRole.ADMIN, AdminRole.OWNER})

def can_ban_users(admin: AdminOut | None) -> bool:
    """Проверить, может ли сотрудник банить и разбанивать клиентов."""
    return has_admin_role(admin, {AdminRole.ADMIN, AdminRole.OWNER})

def can_manage_admins(admin: AdminOut | None) -> bool:
    """Проверить, может ли сотрудник управлять другими сотрудниками."""
    return has_admin_role(admin, {AdminRole.OWNER})


class AdminRoleMiddleware(BaseMiddleware):
    """Middleware для защиты админского sub-router по списку разрешённых ролей."""

    def __init__(self, allowed_roles: Iterable[AdminRole]) -> None:
        """Сохранить роли, которым разрешён доступ к защищаемому sub-router."""
        super().__init__()
        self._allowed_roles = frozenset(allowed_roles)

    async def __call__(
        self,
        handler: Callable[[Message | CallbackQuery, dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: dict[str, Any],
    ) -> Any:
        """Остановить обработку события, если у сотрудника нет нужной роли."""
        if not await require_admin_role(event, data.get("admin"), self._allowed_roles):
            return None
        return await handler(event, data)
