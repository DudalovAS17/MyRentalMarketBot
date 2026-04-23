import logging
from typing import Any, Awaitable, Callable, FrozenSet
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery

from utils.functions import deny
from texts.text_middleware import ONLY_FOR_ADMINS

logger = logging.getLogger(__name__)

class AdminCheckMiddleware(BaseMiddleware):
    """ Middleware для проверки прав администратора (“пользователь — админ”)

    Администратор определяется по whitelist Telegram ID (`admin_ids`), а не по полю пользователя в БД.

    Ожидает, что RegistrationCheckMiddleware уже положил `user` в data["user"].
    """

    def __init__(self, admin_ids: FrozenSet[int]):
        super().__init__()
        self._admin_ids = admin_ids

    async def __call__(
        self,
        handler: Callable[[Message | CallbackQuery, dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: dict[str, Any],
    ) -> Any:

        tg_id = _get_tg_id(event, data)

        if tg_id is None or tg_id not in self._admin_ids:
            logger.warning("[AdminCheckMiddleware] Access denied for user_tg_id=%s", tg_id)
            await deny(event, ONLY_FOR_ADMINS, alert_text="Нет доступа", show_alert=True)
            return None # ✅ КРИТИЧНО: прерываем цепочку, handler не вызывается

        return await handler(event, data)

# ───────────────────────────────────────── helpers ────────────────────────────────────────────────────────────────────
def _get_tg_id(event: Message | CallbackQuery, data: dict[str, Any]) -> int | None:
    """Проверить, входит ли Telegram ID пользователя в whitelist администраторов"""

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