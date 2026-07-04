# AGENT: Handlers

Файл задаёт правила для слоя `handlers/` в `MyRentalMarketBot`.

Нужен агентам, которые:
- анализируют пользовательские и админские flow;
- добавляют или правят `message` / `callback_query` handlers;
- ревьюят границы `handler ↔ service`, `handler ↔ FSM`, `handler ↔ keyboard/text helpers`.

Главный принцип:

> Handler знает, **что показать пользователю и как вести UX-сценарий**, но не знает, **как устроена БД** и **почему действие бизнес-допустимо**.

---

## 1) Scope слоя

`handlers/` — это aiogram UX/FSM/router layer.

Разрешено:
- `Message`, `CallbackQuery`, `FSMContext`;
- router decorators и фильтры `F.*`;
- `callback.answer()`, `message.answer()`, `send_or_edit()`;
- чтение/запись FSM draft-данных;
- callback parsing и простая проверка пользовательского ввода;
- вызов services, полученных через middleware DI;
- сборка короткого UX-текста, выбор клавиатуры/formatter/helper;
- обработка бизнес-исключений (`NotFoundError`, `ConflictError`, domain errors) коротким UX-ответом.

Запрещено:
- прямые вызовы repositories;
- SQLAlchemy, `select`, `session`, ORM-запросы;
- импорт `db.models.*` как рабочего контракта;
- ручная реализация бизнес-политик и статусных переходов;
- broad `except Exception` как обычный путь обработки;
- передача raw FSM dict в service без DTO/нормализации, если это уже business payload.

---

## 2) Каноничный handler-flow

1. Быстро ответить callback, если это callback-handler: `await callback.answer()`.
2. Распарсить вход (`text`, callback id, FSM draft).
3. Сделать только UX-guard: пустой ввод, невалидный id, отсутствующий FSM-context.
4. Собрать DTO (`ItemCreate`, `ItemUpdate`, draft DTO), если данные идут в business-layer.
5. Вызвать service.
6. Получить DTO / primitive result.
7. Отформатировать текст/клавиатуру через helper или локально, если это короткий текст.
8. Ответить пользователю.

---

## 3) Пример message handler

```python
from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from handlers.rentals.router import rental_router
from schemas.user import UserOut
from services.item_service import ItemService


@rental_router.message(F.text == "📦 Каталог")
async def show_catalog(
    message: Message,
    state: FSMContext,
    item_service: ItemService,
    user: UserOut,
) -> None:
    await state.clear()

    items = await item_service.list_all_items(available_only=True, limit=10)
    if not items:
        await message.answer("Пока нет доступных товаров.")
        return

    text = "\n".join(f"• {item.title} — {item.price_text or item.price}" for item in items)
    await message.answer(f"Доступные товары:\n\n{text}")
```

---

## 4) Пример callback handler

```python
from aiogram import F
from aiogram.types import CallbackQuery

from handlers.rentals.router import rental_router
from services.item_service import ItemService
from utils.callbacks import parse_int_id_from_callback
from utils.errors import NotFoundError
from utils.functions import send_or_edit


@rental_router.callback_query(F.data.startswith("item:"))
async def show_item_details(callback: CallbackQuery, item_service: ItemService) -> None:
    await callback.answer()

    item_id = await parse_int_id_from_callback(callback)
    if item_id is None:
        return

    try:
        item = await item_service.get_item_by_id(item_id, strict=True)
    except NotFoundError:
        await callback.answer("Товар не найден", show_alert=True)
        return

    await send_or_edit(callback, f"{item.title}\n\n{item.description or 'Описание скоро появится.'}")
```

---

## 5) FSM правила

FSM в проекте — временное UX-хранилище:
- шаги создания/редактирования товара;
- выбранные ids, page, mode;
- черновик пользовательского ввода;
- id сообщения, которое надо редактировать.

FSM не является business contract.

Перед вызовом service:
- привести draft к Pydantic DTO;
- явно обработать отсутствующие поля;
- не передавать в service весь `state.get_data()` без отбора нужных полей.

---

## 6) Работа с helpers

Для крупных flow держим логику рядом с доменом:
- `handlers/admin/create_item_helpers/*`;
- `handlers/rentals/rental_helpers/*`;
- `handlers/category/category_helpers/*`;
- `handlers/auth/helpers_auth/*`;
- `handlers/support/helpers_support.py`.

Выносим в helpers:
- длинные тексты;
- keyboard builders;
- parse/store/load helpers;
- повторяемые formatters;
- валидацию формы ввода, если она UX-level.

Не выносим в helpers бизнес-решения, которые должен принимать service.

---

## 7) Checklist

- [ ] Handler не импортирует SQLAlchemy и `db.repositories`.
- [ ] Handler получает service через DI, а не создаёт вручную.
- [ ] DTO/user из middleware/service используются вместо ORM.
- [ ] `callback.answer()` вызывается быстро.
- [ ] `strict=False -> None` превращается в UX-guard.
- [ ] `strict=True` business exceptions ловятся локально только для UX-ответа.
- [ ] FSM dict не протекает в service как сырой business payload.
- [ ] Сложные тексты/клавиатуры вынесены в helpers.