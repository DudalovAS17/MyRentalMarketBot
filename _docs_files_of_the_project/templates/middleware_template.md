# Template: Middleware

Middleware в проекте — технический guard или DI-инжектор вокруг aiogram handlers.

Правила:
- Один middleware = одна ответственность.
- Бизнес-логика остаётся в services.
- Middleware может читать service только для технического guard-а (например, загрузить пользователя для регистрации).
- UX-ответы короткие и единообразные через `deny()`.
- Для прерывания цепочки возвращаем `None`.
- В `data` кладём только нужные ключи (`user`, services и т.п.).
- Логи без PII: не логируем телефоны и персональные данные.

---

### Guard middleware

```python
import logging
from typing import Any, Awaitable, Callable, FrozenSet

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message

from services.user_service import UserService
from status.user_status import AccountStatus
from texts.text_middleware import MSG_BANNED, MSG_NEED_PHONE, MSG_NEED_REGISTER
from utils.functions import deny

logger = logging.getLogger(__name__)


class RegistrationCheckMiddleware(BaseMiddleware):
    """Проверяет доступ пользователя в рабочую часть бота."""

    def __init__(self, user_service: UserService, admin_ids: FrozenSet[int]) -> None:
        super().__init__()
        self.user_service = user_service
        self._admin_ids = admin_ids

    def _is_admin(self, tg_user_id: int) -> bool:
        return tg_user_id in self._admin_ids

    async def __call__(
        self,
        handler: Callable[[Message | CallbackQuery, dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: dict[str, Any],
    ) -> Any:
        tg_user_id = _tg_user_id(event)
        if tg_user_id is None:
            logger.warning("[RegistrationCheck] event без tg_user_id, блокируем проход")
            return None

        if _is_start_command(event):
            return await handler(event, data)

        user = await self.user_service.get_by_telegram_id(tg_user_id)
        if user is None and _is_contact_message(event):
            return await handler(event, data)

        if not user:
            logger.info("[RegistrationCheck] Пользователь %s не найден", tg_user_id)
            await deny(event, MSG_NEED_REGISTER)
            return None

        data["user"] = user

        is_admin = self._is_admin(tg_user_id)
        if user.account_status == AccountStatus.BANNED and not is_admin:
            logger.warning("[RegistrationCheck] BANNED пользователь %s попытался выполнить действие", tg_user_id)
            await deny(event, MSG_BANNED)
            return None

        if not user.phone and not _is_contact_message(event):
            logger.info("[RegistrationCheck] Пользователь %s не завершил регистрацию", tg_user_id)
            await deny(event, MSG_NEED_PHONE)
            return None

        return await handler(event, data)


def _tg_user_id(event: Message | CallbackQuery) -> int | None:
    return getattr(getattr(event, "from_user", None), "id", None)


def _is_start_command(event: Message | CallbackQuery) -> bool:
    text = getattr(event, "text", None)
    return isinstance(event, Message) and bool(text) and event.text.startswith("/start")


def _is_contact_message(event: Message | CallbackQuery) -> bool:
    return isinstance(event, Message) and event.contact is not None
```

---

### Services injector middleware

```python
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message


class ServicesMiddleware(BaseMiddleware):
    """Добавляет заранее собранные services в `data` для DI в handlers."""

    def __init__(self, **services) -> None:
        self.services = services

    async def __call__(
        self,
        handler: Callable[[Message | CallbackQuery, dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: dict[str, Any],
    ) -> Any:
        data.update(self.services)
        return await handler(event, data)
```

---

### Checklist
- [ ] Middleware не создаёт repository/service вручную — всё приходит через init или container.
- [ ] Все allow/skip условия явно описаны (`/start`, contact и т.п.).
- [ ] Отказ делает `await deny(...)` и `return None`.
- [ ] В `data` нет случайных ключей и больших объектов.
- [ ] Проверяющий middleware не ловит технические исключения.
- [ ] Global error handler остаётся отдельным middleware.