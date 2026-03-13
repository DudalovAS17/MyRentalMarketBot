# **Template: Middleware**

Правила:
- Один middleware = одна ответственность (auth, регистрация, admin, сервисы, логирование и т.д.).
- Никакой бизнес-логики (она в services). В middleware — только «технические»/доступные проверки.
(никаких repo/service вызовов, кроме чтения data["user"], если его туда положил другой middleware)
- Все UX-ответы — короткие, нейтральные, без подробностей.
- Если нужно прервать цепочку — возвращаем `None` (handler не вызовется).
- В `data` кладём только необходимое и с уникальными ключами.
- Логи — без PII (телефоны, персональные данные — нельзя).

---

### Обязательные элементы шаблона
- что он проверяет (назначение)
- На какие события влияет (Message / CallbackQuery / все TelegramObject)
- что он пропускает (например, `/start`)
- Какие события пропускает без проверки (например, `/start`, `event.contact`)
- что добавляет в `data`
- что делает при отказе (`deny() + return None`)

---

### Каноничный шаблон

```
import logging
from typing import Any, Awaitable, Callable, Dict, Union

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject

from utils.functions import deny

logger = logging.getLogger(__name__)


class ExampleCheckMiddleware(BaseMiddleware):
    """
    Пример middleware:
    - Проверяет доступ
    - При успехе добавляет объект в data
    - При отказе — показывает UX и прерывает цепочку
    """
    
    def __init__(self, *, allowed_ids: set[int]) -> None:
        super().__init__()
        self.allowed_ids = allowed_ids

    async def __call__(
        self,
        handler: Callable[[Union[Message, CallbackQuery], Dict[str, Any]], Awaitable[Any]],
        event: Union[Message, CallbackQuery], # TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        # 1) Идентификация пользователя
        user_id = getattr(event.from_user, "id", None)
        if not user_id:
            logger.warning("[Middleware] event without user_id")
            return None

        # 2) Пропуск команд/условий, необходимых для регистрации (/start)
        if isinstance(event, Message) and event.text and event.text.startswith("/start"):
            return await handler(event, data)

        # 3) Проверка доступа (только техническая логика)
        if int(user_id) not in self.allowed_ids:
            logger.warning("[Middleware] Access denied: user_id=%s", user_id)
            await deny(
                event,
                "⛔ Доступ запрещён.",
                alert_text="Нет доступа",
                show_alert=True,
            )
            return None

        # 4) Докладываем данные в DI-мешок
        data["is_allowed"] = True

        # 5) Продолжаем цепочку
        return await handler(event, data)
```

---

### Checklist
- [ ] Название класса отражает ответственность (`RegistrationCheckMiddleware`, `AdminCheckMiddleware`).
- [ ] Все проверки — технические, без бизнес-логики.
- [ ] Нет лишних `print()`/debug (только logger).
- [ ] Все ранние прерывания возвращают `return None`.
- [ ] В `data` добавлены только необходимые ключи.
- [ ] Условия пропуска (`/start`, `contact`, сервисные команды) описаны явно.
- [ ] deny() используется везде, где нужен отказ (единый UX)

---

### Типовые случаи
1. **Registration check**
   - проверка наличия пользователя
   - проверка телефона
   - проверка блокировки/банов
   - `data["user"] = user`

2. **Admin check**
   - проверка `user_id` в списке админов
   - `deny()` при отказе

3. **Services injector**
   - просто `data.update(services)` - только инжект сервисов
   - не делает проверок

4. **Global error handler**
   - отдельный middleware, и он не должен смешиваться с “проверяющими”.
   - GlobalErrorMiddleware ловит только `Exception` (технические ошибки)
   - Проверяющие middleware НЕ ловят исключения, они только `deny()+return None`
   - бизнес-ошибки не перехватывает
   - не продолжает цепочку после ошибки

---

### Примечания
- Если нужен доступ к сервисам — они должны попадать через DI (`data`), а не создаваться в middleware.
- Для отказа всегда используем `deny()` чтобы UX был консистентным.
- Middleware должен быть максимально предсказуемым и коротким.