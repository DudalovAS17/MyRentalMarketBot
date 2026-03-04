from __future__ import annotations
import logging
from typing import Any, Awaitable, Callable, Dict, Union, Iterable

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

    def __init__(self, admin_ids: Iterable[int]):
        super().__init__()
        self.admin_ids = set(admin_ids) # set(int(x) for x in admin_ids)

    async def __call__(
        self,
        handler: Callable[[Union[Message, CallbackQuery], Dict[str, Any]], Awaitable[Any]],
        event: Union[Message, CallbackQuery],
        data: Dict[str, Any],
    ) -> Any:
        tg_id = None

        user = data.get("user") # user из RegistrationCheckMiddleware
        if user is not None:
            tg_id = getattr(user, "telegram_id", None)

        print("ADMIN CHECK")
        print("admin_ids =", self.admin_ids)
        print("event.from_user.id =", event.from_user.id)
        print("user from data =", data.get("user"))

        # Но на всякий случай умеет брать tg_id из event.from_user.id.
        #if tg_id is None: # and getattr(event, "from_user", None):
        #    tg_id = getattr(event.from_user, "id", None)

        # deny() - цель: “нет доступа, объяснить быстро и оставить след”

        if tg_id is None or int(tg_id) not in self.admin_ids: # int(tg_id) - возможно нужна функция-проверка на int
            logger.warning("[Admin] Access denied for user_tg_id=%s", tg_id)
            text = "⛔ Доступ запрещён. Раздел доступен только администраторам."

            await deny(event, text, alert_text="Нет доступа", show_alert=True)
            return None # ✅ КРИТИЧНО: прерываем цепочку, handler не вызывается

        return await handler(event, data)

