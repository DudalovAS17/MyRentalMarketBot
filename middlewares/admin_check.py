"""Middleware проверки доступа сотрудников к админским handlers."""

import logging
from typing import Any, Awaitable, Callable, FrozenSet
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery

from services.admin_directory_service import AdminDirectoryService
from status.user_status import AccountStatus
from utils.functions import deny
from texts.text_middleware import ONLY_FOR_ADMINS, ADMIN_PROFILE_REQUIRED

logger = logging.getLogger(__name__)

class AdminCheckMiddleware(BaseMiddleware):
    """Проверяет, что событие пришло от активного сотрудника админки.

    Telegram ID должен быть в `ADMIN_IDS`, а профиль сотрудника в таблице `admins` должен существовать,
    быть активным и не заблокированным. Загруженный профиль кладётся в `data["admin"]` для последующих проверок ролей.

    Ожидает, что RegistrationCheckMiddleware уже положил `user` в data["user"].
    """

    def __init__(self, admin_ids: FrozenSet[int], admin_directory_service: AdminDirectoryService):
        super().__init__()
        self._admin_ids = admin_ids
        self._admin_directory_service = admin_directory_service

    async def __call__(
        self,
        handler: Callable[[Message | CallbackQuery, dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: dict[str, Any],
    ) -> Any:
        """Прервать обработку события, если сотрудник не прошёл admin-check."""
        tg_id = _get_tg_id(event, data)

        if tg_id is None or tg_id not in self._admin_ids:
            logger.warning("[AdminCheckMiddleware] Access denied for user_tg_id=%s", tg_id)
            await deny(event, ONLY_FOR_ADMINS, alert_text="Нет доступа", show_alert=True)
            return None # ✅ КРИТИЧНО: прерываем цепочку, handler не вызывается

        admin = await self._admin_directory_service.get_by_telegram_id(tg_id)
        if admin is None or not admin.is_active or admin.account_status != AccountStatus.ACTIVE:
            logger.warning("[AdminCheckMiddleware] Inactive/missing admin profile for tg_id=%s", tg_id)
            await deny(event, ADMIN_PROFILE_REQUIRED, alert_text="Нет доступа", show_alert=True)
            return None

        data["admin"] = admin
        return await handler(event, data)

# ───────────────────────────────────────── helpers ────────────────────────────────────────────────────────────────────
def _get_tg_id(event: Message | CallbackQuery, data: dict[str, Any]) -> int | None:
    """Получить Telegram ID из DTO пользователя или напрямую из Telegram-события."""

    # Если user уже загружен (RegistrationCheckMiddleware)
    user = data.get("user")
    if user is not None:
        tg_id = getattr(user, "telegram_id", None)
        if tg_id is not None:
            return int(tg_id)

    # Иначе:
    from_user = getattr(event, "from_user", None)
    if from_user is None:
        return None

    event_tg_id = getattr(from_user, "id", None)
    return int(event_tg_id) if event_tg_id is not None else None