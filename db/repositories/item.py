from typing import Optional
from sqlalchemy import select, or_
from datetime import datetime, timezone

from db.models.item import Item
from db.repositories.base import BaseRepository

from schemas.item import ItemCreate, ItemUpdate
from status.item_status import ItemStatus


class ItemRepository(BaseRepository):
    """Репозиторий объявлений"""

    # ───────────────────────────────────────────────────────────────────────────────────────────────────────
    @staticmethod
    def _apply_active_filter(stmt):
        return (
            stmt.where(Item.status == ItemStatus.ACTIVE)
        ) # доступные=активные

    # ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    async def list_all(self, *, active_only: bool = True, limit: Optional[int] = None, offset: int = 0) -> list[Item]:
        """Все объявления (по умолчанию только активные=доступные)"""
        async with self._session() as s:
            stmt = select(Item)
            if active_only:
                stmt = self._apply_active_filter(stmt)

            if limit is not None:
                stmt = stmt.limit(limit).offset(offset)
            #stmt = stmt.offset(offset)
            #if limit is not None:
            #    stmt = stmt.limit(limit)

            return await self._list(s, stmt)

    async def get_by_id(self, item_id: int) -> Optional[Item]:
        """Объявление по ID"""
        async with self._session() as s:
            return await s.get(Item, item_id)

    async def list_by_user_id(self, user_id: int, *, active_only: bool = False) -> list[Item]:
        """Все объявления владельца. При active_only=True — только ACTIVE, active_only=False - все объявления владельца"""
        async with self._session() as s:
            stmt = select(Item).where(Item.user_id == user_id)
            if active_only:
                stmt = self._apply_active_filter(stmt)

            return await self._list(s, stmt)

    async def list_by_category(self, category_id: int, *, active_only: bool = True) -> list[Item]:
        """Получает все активные=доступные объявления по категории"""
        async with self._session() as s:
            stmt = select(Item).where(Item.category_id == category_id)
            if active_only:
                stmt = self._apply_active_filter(stmt)

            return await self._list(s, stmt)

    async def list_by_subcategory(self, subcategory_id: int, *, active_only: bool = True) -> list[Item]:
        """Получает все активные=доступные объявления по подкатегории"""
        async with self._session() as s:
            stmt = select(Item).where(Item.subcategory_id == subcategory_id)
            if active_only:
                stmt = self._apply_active_filter(stmt)

            return await self._list(s, stmt)

    async def search(self, query: str, *, active_only: bool = True, limit: int = 50, offset: int = 0) -> list[Item]:
        """Поиск объявлений по тексту. По названию ИЛИ описанию"""
        q = f"%{query.strip()}%"
        async with self._session() as s:
            stmt = select(Item).where(or_(Item.title.ilike(q), Item.description.ilike(q)))
            if active_only:
                stmt = self._apply_active_filter(stmt)
            stmt = stmt.limit(limit).offset(offset)

            return await self._list(s, stmt)

    # ──────────────────────────────────────────── NEW (Admin-Item logic) ────────────────────────────────────────
    async def list_by_status(self, status: ItemStatus, limit: int, offset: int = 0) -> list[Item]:
        """Объявления на модерации по статусу, по убыванию id"""
        async with self._session() as s:
            stmt = (
                select(Item)
                .where(Item.status == status)
                .order_by(Item.id.desc())
                .limit(limit)
                .offset(offset)
            )

            return await self._list(s, stmt)

    async def list_pending(self, limit: int, offset: int = 0) -> list[Item]:
        """Объявления на модерации - PENDING"""
        return await self.list_by_status(status=ItemStatus.PENDING, limit=limit, offset=offset)

    async def set_status(self,
        item_id: int,
        new_status: ItemStatus,
        admin_user_id: int,
        reason: Optional[str] = None,
    ) -> Optional[Item]:
        """Техническое обновление статуса объявления. Бизнес-проверки выполняет сервис (whitelist)."""
        async with self._session() as s:
            obj: Optional[Item] = await s.get(Item, item_id)
            if not obj:
                return None

            obj.status = new_status
            obj.moderated_at = datetime.now(timezone.utc)
            obj.moderated_by_admin_id = admin_user_id
            if reason is not None:
                obj.moderation_reason = reason

            return await self._commit_refresh(s, obj)

    # ───────────────────────────────────────────────────────────────────────────────────────────────────────
    async def create(self,  user_id: int, item_data: ItemCreate) -> Item:
        """Создать объявление"""
        obj = Item(user_id=user_id, **item_data.model_dump())
        async with self._session() as s:
            return await self._add_commit_refresh(s, obj)

    async def update(self, item_id: int,  update_data: ItemUpdate) -> Optional[Item]:
        """Обновить поля объявления (только переданные)

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

            for k, v in data.items():
                setattr(obj, k, v)

            return await self._commit_refresh(s, obj)

    async def delete(self, item_id: int) -> bool:
        """Удалить объявление. True — удалено, False — не найдено/ошибка"""
        async with self._session() as s:
            obj = await s.get(Item, item_id)
            if not obj:
                return False

            return await self._delete_commit(s, obj)