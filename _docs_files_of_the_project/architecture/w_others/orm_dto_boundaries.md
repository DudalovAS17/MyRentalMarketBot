# ORM и DTO: границы слоёв

Документ фиксирует актуальное правило разделения SQLAlchemy ORM-моделей и Pydantic DTO в проекте.

Главная идея: ORM живёт внутри persistence/business слоёв, а наружу из service в handler выходит только DTO или primitive.

---

## 1) ORM

ORM — это SQLAlchemy-модели из `db/models/`.

Свойства ORM:

- напрямую связаны с таблицами БД;
- живут в контексте SQLAlchemy session;
- могут иметь lazy/eager relationships;
- мутируемы;
- требуют аккуратного commit/rollback/refresh;
- не являются безопасным контрактом для Telegram/FSM/UI слоя.

ORM разрешён в:

- `db/models/`;
- `db/repositories/`;
- `services/` только как внутренний результат repository перед маппингом в DTO.

ORM запрещён как рабочий контракт в:

- `handlers/`;
- `keyboards/`;
- `texts/` / formatters;
- FSM state.

---

## 2) DTO

DTO — это Pydantic-схемы из `schemas/`.

Типы DTO:

- `XxxCreate` — входные данные для создания;
- `XxxUpdate` — partial update, обычно применяется через `model_dump(exclude_unset=True)`;
- `XxxOut` — безопасный output из service в handlers;
- `XxxDraft` / `XxxInternal` / `XxxAdminOut` — отдельные контракты для FSM, внутренних сценариев или админки, если нужны.

`Out`-схемы, которые строятся из ORM, должны иметь:

```python
model_config = ConfigDict(from_attributes=True)
```

DTO разрешён в:

- `schemas/`;
- `services/`;
- `handlers/`;
- `keyboards/`, helpers, formatters.

---

## 3) Таблица контрактов

| Слой | Принимает | Возвращает |
| --- | --- | --- |
| `db/models` | — | ORM definitions |
| `db/repositories` | primitive ids, DTO для create/update допустимы | ORM / `list[ORM]` / primitive |
| `services` | primitive args, DTO, actor ids | DTO / `list[DTO]` / `None` / `bool` / `int` |
| `handlers` | Telegram events, FSM, DTO из middleware/service | Telegram responses |
| `keyboards` / helpers / formatters | DTO / primitive | markup/text |

Важно: repository может принимать `Create`/`Update` DTO как вход для записи, но не должен возвращать DTO. Граница ORM → DTO находится в service.

---

## 4) Каноничный поток данных

Repository возвращает ORM:

```python
async def get_by_id(self, item_id: int) -> Item | None:
    async with self._session() as session:
        return await session.get(Item, item_id)
```

Service переводит ORM в DTO:

```python
async def get_item_by_id(self, item_id: int, *, strict: bool = False) -> ItemOut | None:
    item = await self.item_repo.get_by_id(item_id)
    if not item:
        if strict:
            raise NotFoundError(f"Товар не найден: id={item_id}")
        return None
    return ItemOut.model_validate(item)
```

Handler работает только с DTO:

```python
item = await item_service.get_item_by_id(item_id, strict=True)
await callback.message.answer(item.title)
```

---

## 5) Почему ORM не выходит в handlers

Если передавать ORM наружу, появляются риски:

- lazy-load после закрытия session;
- случайные SQL-запросы в UI-layer;
- утечки SQLAlchemy details в Telegram/FSM код;
- сложные side effects при мутировании объекта;
- трудный рефакторинг схем и repository;
- неявная зависимость handlers от структуры БД.

DTO делает контракт явным и стабильным.

---

## 6) Чеклист

- [ ] Repository возвращает ORM/primitive, а не DTO.
- [ ] Service маппит ORM → DTO через `model_validate()`.
- [ ] Handler не импортирует `db.models.*` как рабочий контракт.
- [ ] Handler не передаёт ORM в FSM/keyboards/text helpers.
- [ ] `Update` применяется через `exclude_unset=True`.
- [ ] `Out`-DTO имеет `ConfigDict(from_attributes=True)`.