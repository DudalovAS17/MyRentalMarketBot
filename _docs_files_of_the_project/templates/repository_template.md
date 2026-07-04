## Template: Repository

Репозиторий в этом проекте — тонкий SQLAlchemy-слой над ORM-моделью.

Правила:
- Наследуемся от `BaseRepository`.
- Работаем только с ORM и SQLAlchemy (`select`, `update`, `delete`, relationships при необходимости).
- Не возвращаем Pydantic/DTO наружу — только ORM / `list[ORM]` / `bool` / `None`.
- Не знаем про Telegram, FSM, handlers и тексты UX.
- Не держим бизнес-правила: проверки статусов, конфликтов и сценариев живут в service.
- Для чтения используем `_session()`, `_list()`, `_one_or_none()`, `_exists()`.
- Для записи используем `_add_commit_refresh()`, `_commit_refresh()`, `_delete_commit()` или `_execute_update_commit()`.
- Для update всегда применяем `model_dump(exclude_unset=True)`, чтобы не затереть поля в `None` случайно.

---

### Каноничный шаблон

```python
from typing import Optional

from sqlalchemy import select

from db.models.item import Item
from db.repositories.base import BaseRepository
from schemas.item import ItemCreate, ItemUpdate
from status.item_status import ItemStatus


class ItemRepository(BaseRepository):
    """Репозиторий товаров каталога компании."""

    # ───────────────────────────────────── helpers ─────────────────────────────────────
    @staticmethod
    def _apply_active_filter(stmt):
        """Оставить только опубликованные/активные товары каталога."""
        return stmt.where(Item.status == ItemStatus.ACTIVE)

    @staticmethod
    def _apply_catalog_order(stmt):
        """Стабильный порядок выдачи товаров в каталоге."""
        return stmt.order_by(Item.sort_order.asc(), Item.id.desc())

    @staticmethod
    def _apply_pagination(stmt, *, limit: Optional[int], offset: int):
        if limit is not None:
            stmt = stmt.limit(limit).offset(offset)
        return stmt

    # ───────────────────────────────────── reads ───────────────────────────────────────
    async def list_all(
        self,
        *,
        active_only: bool = True,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> list[Item]:
        """Все товары каталога; по умолчанию только опубликованные."""
        async with self._session() as s:
            stmt = select(Item)
            if active_only:
                stmt = self._apply_active_filter(stmt)

            stmt = self._apply_catalog_order(stmt)
            stmt = self._apply_pagination(stmt, limit=limit, offset=offset)
            return await self._list(s, stmt)

    async def get_by_id(self, item_id: int) -> Optional[Item]:
        """Товар каталога по ID."""
        async with self._session() as s:
            return await s.get(Item, item_id)

    async def list_by_category(self, category_id: int, *, active_only: bool = True) -> list[Item]:
        """Получить товары каталога по категории."""
        async with self._session() as s:
            stmt = select(Item).where(Item.category_id == category_id)
            if active_only:
                stmt = self._apply_active_filter(stmt)

            stmt = self._apply_catalog_order(stmt)
            return await self._list(s, stmt)

    # ───────────────────────────────────── writes ──────────────────────────────────────
    async def create(
        self,
        *,
        item_data: ItemCreate,
        created_by_admin_id: Optional[int] = None,
        status: ItemStatus = ItemStatus.DRAFT,
    ) -> Item:
        """Создать товар каталога. Возвращает ORM-объект."""
        data = item_data.model_dump(exclude_none=True)
        obj = Item(
            **data,
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
        """Частично обновить товар каталога. Возвращает ORM или None."""
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

    async def delete(self, item_id: int) -> bool:
        """Удалить товар по ID. True — удалён, False — не найден."""
        async with self._session() as s:
            obj = await s.get(Item, item_id)
            if not obj:
                return False
            return await self._delete_commit(s, obj)
```

---

### Checklist
- [ ] Репозиторий наследуется от `BaseRepository`.
- [ ] Метод чтения возвращает ORM или список ORM.
- [ ] Метод записи делает commit только через helper из `BaseRepository`.
- [ ] `Update` применяет `exclude_unset=True`.
- [ ] Нет `message`, `callback`, `FSMContext`, `Router`, `Keyboard`, `deny()`.
- [ ] Нет бизнес-ошибок уровня `NotFoundError` / `ConflictError` — это слой service.
- [ ] Фильтры/сортировки вынесены в маленькие `_apply_*` helpers, если переиспользуются.