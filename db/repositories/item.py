from typing import Optional
from sqlalchemy import select, or_
from datetime import datetime, timezone

from db.models.item import Item
from db.models.item_characteristics import ItemCharacteristic
from db.repositories.base import BaseRepository

from schemas.item import ItemCreate, ItemUpdate
from status.item_status import ItemStatus


class ItemRepository(BaseRepository):
    """Репозиторий товаров каталога компании."""

    # ───────────────────────────────────────────────────────────────────────────────────────────────────────
    @staticmethod
    def _apply_active_filter(stmt):
        """Оставить только опубликованные/активные товары каталога."""
        return stmt.where(Item.status == ItemStatus.ACTIVE) # , Item.available_quantity > 0

    @staticmethod
    def _apply_catalog_order(stmt):
        """Стабильный порядок выдачи товаров в каталоге."""
        return stmt.order_by(Item.sort_order.asc(), Item.title.asc(), Item.id.desc())

    @staticmethod
    def _apply_pagination(stmt, *, limit: Optional[int], offset: int):
        if limit is not None:
            stmt = stmt.limit(limit).offset(offset)
        return stmt

    # ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    async def list_all(self, *, active_only: bool = True, limit: Optional[int] = None, offset: int = 0) -> list[Item]:
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

    async def get_public_by_id(self, item_id: int) -> Optional[Item]:
        """Опубликованный товар, который можно показывать клиенту в каталоге."""
        async with self._session() as s:
            stmt = select(Item).where(Item.id == item_id)
            stmt = self._apply_active_filter(stmt)
            return await self._one_or_none(s, stmt)

    async def list_by_created_admin_id(self, admin_id: int, *, active_only: bool = False) -> list[Item]:
        """Все товары каталога, созданные указанным администратором/менеджером."""
        async with self._session() as s:
            stmt = select(Item).where(Item.created_by_admin_id == admin_id)
            if active_only:
                stmt = self._apply_active_filter(stmt)

            stmt = self._apply_catalog_order(stmt)
            return await self._list(s, stmt)

    async def list_by_updated_admin_id(self, admin_id: int, *, active_only: bool = False) -> list[Item]:
        """Все товары каталога, последний раз обновлённые указанным администратором/менеджером."""
        async with self._session() as s:
            stmt = select(Item).where(Item.updated_by_admin_id == admin_id)
            if active_only:
                stmt = self._apply_active_filter(stmt)

            stmt = self._apply_catalog_order(stmt)
            return await self._list(s, stmt)

    async def list_by_category(self, category_id: int, *, active_only: bool = True) -> list[Item]:
        """Получить товары каталога по категории."""
        async with self._session() as s:
            stmt = select(Item).where(Item.category_id == category_id)
            if active_only:
                stmt = self._apply_active_filter(stmt)

            stmt = self._apply_catalog_order(stmt)
            return await self._list(s, stmt)

    async def list_by_subcategory(self, subcategory_id: int, *, active_only: bool = True) -> list[Item]:
        """Получить товары каталога по подкатегории."""
        async with self._session() as s:
            stmt = select(Item).where(Item.subcategory_id == subcategory_id)
            if active_only:
                stmt = self._apply_active_filter(stmt)

            stmt = self._apply_catalog_order(stmt)
            return await self._list(s, stmt)

    async def search(self, query: str, *, active_only: bool = True, limit: int = 50, offset: int = 0) -> list[Item]:
        """Поиск товаров по тексту: по названию, описанию или характеристикам."""
        q = f"%{query.strip()}%"
        async with self._session() as s:
            stmt = (
                select(Item)
                .outerjoin(ItemCharacteristic, ItemCharacteristic.item_id == Item.id)
                .where(
                    or_(
                        Item.title.ilike(q),
                        Item.description.ilike(q),
                        Item.short_description.ilike(q),
                        ItemCharacteristic.name.ilike(q),
                        ItemCharacteristic.value.ilike(q),
                    )
                )
                .distinct()
            )

            if active_only:
                stmt = self._apply_active_filter(stmt)

            stmt = self._apply_catalog_order(stmt)
            stmt = self._apply_pagination(stmt, limit=limit, offset=offset)
            return await self._list(s, stmt)

    # ──────────────────────────────────────────── Admin-Item logic ────────────────────────────────────────────────────
    async def list_by_status(self, status: ItemStatus, limit: int, offset: int = 0) -> list[Item]:
        """Товары каталога по статусу с пагинацией."""
        async with self._session() as s:
            stmt = (
                select(Item)
                .where(Item.status == status)
                .order_by(Item.sort_order.asc(), Item.id.desc())
                .limit(limit)
                .offset(offset)
            )

            return await self._list(s, stmt)

    async def list_drafts(self, limit: int, offset: int = 0) -> list[Item]:
        """Черновики товаров каталога."""
        return await self.list_by_status(status=ItemStatus.DRAFT, limit=limit, offset=offset)

    async def set_status(self, item_id: int, new_status: ItemStatus, updated_by_admin_id: Optional[int] = None) -> Optional[Item]:
        """Техническое обновление статуса товара каталога; бизнес-проверки выполняет сервис."""
        async with self._session() as s:
            obj: Optional[Item] = await s.get(Item, item_id)
            if not obj:
                return None

            obj.status = new_status
            obj.moderated_at = datetime.now(timezone.utc)
            if updated_by_admin_id is not None:
                obj.updated_by_admin_id = updated_by_admin_id

            return await self._commit_refresh(s, obj)

    # ───────────────────────────────────────────────────────────────────────────────────────────────────────
    async def create(
            self,
            item_data: ItemCreate,
            *,
            created_by_admin_id: Optional[int] = None,
            status: ItemStatus = ItemStatus.DRAFT
    ) -> Item:
        """Создать товар каталога компании."""
        obj = Item(
            **item_data.model_dump(exclude_none=True),
            created_by_admin_id=created_by_admin_id,
            status=status,
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
        """Обновить поля товара каталога.

        - если item не найден → None
        - если patch пустой → вернуть текущий ORM без commit
        - если изменения есть → применить и сделать commit_refresh
        """
        async with self._session() as s:
            obj: Optional[Item] = await s.get(Item, item_id)
            if not obj:
                return None

            data = update_data.model_dump(exclude_unset=True)
            if not data:
                return obj

            changed = False
            for field_name, value in data.items():
                if getattr(obj, field_name) != value:
                    setattr(obj, field_name, value)
                    changed = True

            if not changed:
                return obj

            if updated_by_admin_id is not None:
                obj.updated_by_admin_id = updated_by_admin_id

            return await self._commit_refresh(s, obj)

    async def delete(self, item_id: int) -> bool:
        """Удалить товар каталога. True — удалён, False — не найден."""
        async with self._session() as s:
            obj = await s.get(Item, item_id)
            if not obj:
                return False

            return await self._delete_commit(s, obj)



    # ─────────────────────────────────────────────Item Characteristic──────────────────────────────────────────────────
    async def list_characteristics_by_item_id(self, item_id: int, limit: Optional[int] = None) -> list[ItemCharacteristic]:
        """Вернуть характеристики товара в порядке отображения."""
        async with self._session() as s:
            stmt = (
                select(ItemCharacteristic)
                .where(ItemCharacteristic.item_id == item_id)
                .order_by(ItemCharacteristic.sort_order.asc(), ItemCharacteristic.id.asc())
            )
            if limit is not None:
                stmt = stmt.limit(limit)
            return await self._list(s, stmt)