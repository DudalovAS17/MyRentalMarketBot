from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable, Union, FrozenSet
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery

from utils.functions import deny

logger = logging.getLogger(__name__)

class AdminCheckMiddleware(BaseMiddleware):
    """
    Middleware для проверки прав администратора.

    Ожидает, что RegistrationCheckMiddleware уже положил `user` в data["user"].

    RegistrationCheck = “пользователь существует, не заблокирован, есть телефон”
    AdminCheck = “пользователь — админ”
    """

    def __init__(self, admin_ids: FrozenSet[int]):
        super().__init__()
        self._admin_ids = admin_ids

    async def __call__(
        self,
        handler: Callable[[Union[Message, CallbackQuery], dict[str, Any]], Awaitable[Any]],
        event: Union[Message, CallbackQuery],
        data: dict[str, Any],
    ) -> Any:

        tg_id = _get_tg_id(event, data)

        if tg_id is None or tg_id not in self._admin_ids:
            logger.warning("[AdminCheckMiddleware] Access denied for user_tg_id=%s", tg_id)
            text = "⛔ Доступ запрещён. Раздел доступен только администраторам."
            await deny(event, text, alert_text="Нет доступа", show_alert=True)
            return None # ✅ КРИТИЧНО: прерываем цепочку, handler не вызывается

        return await handler(event, data)


def _get_tg_id(event: Message | CallbackQuery, data: dict[str, Any]) -> int | None:
    # 1) Основной путь: user уже загружен RegistrationCheckMiddleware
    # print("user from data =", data.get("user"))
    user = data.get("user")
    if user is not None:
        tg_id = getattr(user, "telegram_id", None)
        if tg_id is not None:
            return int(tg_id)

    # 2) Иначе: берём из update (на случай, если порядок middleware поменяли)
    # print("event.from_user.id =", event.from_user.id)
    from_user = getattr(event, "from_user", None)
    if from_user is None:
        return None

    return getattr(from_user, "id", None)