# Template: Handler

Handler в этом проекте — слой UX/FSM/Router. Он принимает Telegram event, достаёт входные данные, вызывает service и отвечает пользователю.

Правила:
- Только UX, FSM, Router, keyboards, форматирование ответа.
- Никаких ORM/SQLAlchemy/repositories.
- Минимум бизнес-логики: сложные проверки уходят в service.
- Service приходит через DI из middleware (`data`).
- DTO/user приходят из middleware или service.
- Бизнес-ошибки (`NotFoundError`, `ConflictError`) превращаем в понятный UX.
- Технические ошибки не глотаем — их ловит global error handler.

---

### Каноничный шаблон message handler

```python
import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from handlers.rentals.router import rental_router
from schemas.user import UserOut
from services.item_service import ItemService
from utils.errors import NotFoundError

logger = logging.getLogger(__name__)


@rental_router.message(F.text == "📦 Каталог")
async def show_catalog(
    message: Message,
    state: FSMContext,
    item_service: ItemService,
    user: UserOut,
) -> None:
    """UX/FSM: показать пользователю товары каталога."""
    await state.clear()

    items = await item_service.list_all_items(available_only=True, limit=10)
    if not items:
        await message.answer("Пока нет доступных товаров.")
        return

    text = "\n".join(f"• {item.title} — {item.price_text or item.price}" for item in items)
    await message.answer(f"Доступные товары:\n\n{text}")
```

---

### Каноничный шаблон callback handler

```python
import logging

from aiogram import F
from aiogram.types import CallbackQuery

from handlers.rentals.router import rental_router
from services.item_service import ItemService
from utils.callbacks import parse_int_id_from_callback
from utils.errors import NotFoundError
from utils.functions import send_or_edit

logger = logging.getLogger(__name__)


@rental_router.callback_query(F.data.startswith("item:"))
async def show_item_details(
    callback: CallbackQuery,
    item_service: ItemService,
) -> None:
    """UX: открыть карточку товара по callback."""
    await callback.answer()

    item_id = await parse_int_id_from_callback(callback)
    if item_id is None:
        return

    try:
        item = await item_service.get_item_by_id(item_id, strict=True)
    except NotFoundError:
        await callback.answer("Товар не найден", show_alert=True)
        return

    await send_or_edit(
        callback,
        f"{item.title}\n\n{item.description or 'Описание скоро появится.'}",
    )
```

---

### FSM guard в handler — это нормально

Если service возвращает `None` при `strict=False`, UX-guard остаётся ответственностью handler-а:

```python
item = await item_service.get_item_by_id(item_id, strict=False)
if item is None:
    await message.answer("Товар не найден или уже скрыт.")
    return
```

---

### Checklist
- [ ] В handler нет SQLAlchemy и repository imports.
- [ ] Вся бизнес-логика находится в service.
- [ ] `callback.answer()` вызывается быстро.
- [ ] FSM очищается/меняется только там, где это часть UX-сценария.
- [ ] Ошибки service превращаются в короткие сообщения пользователю.
- [ ] Форматирование длинных текстов вынесено в helper/formatter, если оно переиспользуется.