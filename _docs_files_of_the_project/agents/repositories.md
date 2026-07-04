# AGENT: Repositories

Файл задаёт правила для слоя `db/repositories/` в `MyRentalMarketBot`.

Нужен агентам, которые:
- анализируют SQLAlchemy-запросы;
- добавляют repository-классы и методы;
- ревьюят границу `service ↔ repository`;
- чинят persistence/read/write операции.

Главный принцип:

> Repository знает, **как читать и писать данные**, но не знает, **зачем бизнес это делает**.

---

## 1) Scope слоя

`db/repositories/` — persistence/query layer.

Разрешено:
- SQLAlchemy `select`, `update`, `delete`, `exists`, filters, joins;
- ORM-модели из `db.models.*`;
- `AsyncSession` только через `BaseRepository` session factory;
- commit/rollback/refresh через helpers `BaseRepository`;
- eager loading, если service после закрытия сессии должен безопасно читать связи;
- возврат ORM / `list[ORM]` / primitive (`bool`, `int`, scalar).

Запрещено:
- Telegram/FSM/UI объекты;
- Pydantic DTO как output-контракт;
- user-facing тексты;
- бизнес-решения, статусная policy, ownership checks как источник истины;
- создание сессий в обход `_session()`;
- скрытое проглатывание DB-ошибок.

---

## 2) BaseRepository — обязательный канон

Все новые repositories наследуются от `BaseRepository`.

Используем:
- `_session()` для открытия `AsyncSession`;
- `_list()` для списков;
- `_one_or_none()` для single-result queries;
- `_exists()` для exists/scalar bool;
- `_add_commit_refresh()` для create;
- `_commit_refresh()` для update с возвратом ORM;
- `_delete_commit()` для delete;
- `_execute_update_commit()` для atomic `UPDATE ... WHERE ...`.

Не дублируем try/rollback/commit руками, если уже есть helper.

---

## 3) Каноничный CRUD pattern

```python
from typing import Optional

from sqlalchemy import select

from db.models.item import Item
from db.repositories.base import BaseRepository
from schemas.item import ItemCreate, ItemUpdate
from status.item_status import ItemStatus


class ItemRepository(BaseRepository):
    """Репозиторий товаров каталога компании."""

    async def get_by_id(self, item_id: int) -> Optional[Item]:
        async with self._session() as s:
            return await s.get(Item, item_id)

    async def list_by_category(self, category_id: int, *, active_only: bool = True) -> list[Item]:
        async with self._session() as s:
            stmt = select(Item).where(Item.category_id == category_id)
            if active_only:
                stmt = stmt.where(Item.status == ItemStatus.ACTIVE)
            stmt = stmt.order_by(Item.sort_order.asc(), Item.id.desc())
            return await self._list(s, stmt)

    async def create(
        self,
        *,
        item_data: ItemCreate,
        created_by_admin_id: Optional[int] = None,
        status: ItemStatus = ItemStatus.DRAFT,
    ) -> Item:
        obj = Item(
            **item_data.model_dump(exclude_none=True),
            status=status,
            created_by_admin_id=created_by_admin_id,
            updated_by_admin_id=created_by_admin_id,
        )
        async with self._session() as s:
            return await self._add_commit_refresh(s, obj)

    async def update(
        self,
        item_id: int,
        update_data: ItemUpdate,
        *,
        updated_by_admin_id: Optional[int] = None,
    ) -> Optional[Item]:
        data = update_data.model_dump(exclude_unset=True)

        async with self._session() as s:
            obj = await s.get(Item, item_id)
            if not obj:
                return None

            changed = False
            for field_name, value in data.items():
                if getattr(obj, field_name) != value:
                    setattr(obj, field_name, value)
                    changed = True

            if updated_by_admin_id is not None and obj.updated_by_admin_id != updated_by_admin_id:
                obj.updated_by_admin_id = updated_by_admin_id
                changed = True

            if not changed:
                return obj

            return await self._commit_refresh(s, obj)
```

---

## 4) Update rules

Partial update:
- только `model_dump(exclude_unset=True)`;
- `None` означает “пользователь явно передал null”, если поле nullable;
- unset означает “не менять поле”.

Если значения не изменились:
- можно вернуть ORM без commit;
- не делать лишний write.

Atomic update:
- используем `update(...).where(...)` + `_execute_update_commit()`;
- хорош для status/flag transitions и stale-button protection;
- возвращает `bool` по `rowcount`.

---

## 5) ID rules

Не смешивать:
- `id`, `user_id`, `item_id`, `rental_id`, `admin_id` — DB PK/FK;
- `telegram_id`, `admin_tg_id`, `*_tg_id` — внешний Telegram ID.

Repository должен фильтровать по полю, соответствующему типу ID.

---

## 6) Checklist

- [ ] Repository наследуется от `BaseRepository`.
- [ ] Возвращает ORM/primitive, не DTO.
- [ ] Не содержит Telegram/FSM/UI.
- [ ] Не решает бизнес-policy.
- [ ] Write-операции используют commit helpers.
- [ ] `Update` использует `exclude_unset=True`.
- [ ] Нужные сортировки/фильтры стабильны и предсказуемы.
- [ ] Eager loading добавлен только когда он нужен read-case’у.