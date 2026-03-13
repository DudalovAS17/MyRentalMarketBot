# Handler
- ловит бизнес-ошибки (utils/errors.py) и показывает человеку понятное сообщение
  - технические ошибки:
    - либо не ловим вообще (пусть падает и будет видно в логах)
    - либо ловим одним общим middleware/error-handler

--- 
### Глобальный error middleware - на будущее
💡 Проф-решение: единый global error handler / middleware, а не try/except в каждом хендлере.
- перехватывает исключения
- залогировать один раз
- показать нейтральное “⚠️ Ошибка. Попробуйте позже.”
- ❌ НЕ ловим Exception (технические ошибки уходят в глобальный обработчик)
--- 

### **utils/errors.py ->** Handler сможет
- различать типы
- отдавать разные сообщения (например: «не найдено» vs «недостаточно прав»), а не всё под одно сообщение.

---

### ✅ Что фиксируем для handler-template

*handlers ловят ServiceError (и наследников) → показывают UX-сообщение*

*технические ошибки → глобальный error handler (позже) или падают (на этапе рефакторинга лучше global)*

Минимально для шаблона handler:
```
from utils.errors import ServiceError, NotFoundError

try:
    ...
except NotFoundError:
    await callback.answer("Не найдено", show_alert=True)
except ServiceError as e:
    await callback.answer(str(e), show_alert=True)
```