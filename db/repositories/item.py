from __future__ import annotations

from typing import Optional, List
from sqlalchemy import select, or_
from datetime import datetime, timezone

from schemas.item import ItemCreate, ItemUpdate
from status.item_status import ItemStatus
from db.models.item import Item
from db.repositories.base import BaseRepository


class ItemRepository(BaseRepository):
    """Репозиторий объявлений"""
    # ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    async def list_all(self, *, available_only: bool = True, limit: Optional[int] = None, offset: int = 0) -> List[Item]:
        """Все объявления (по умолчанию только доступные)"""
        async with self._session() as s:
            stmt = select(Item)
            if available_only:
                stmt = self._apply_available_active_filter(stmt)

            if limit is not None:
                stmt = stmt.limit(limit).offset(offset)
            #stmt = stmt.offset(offset)
            #if limit is not None:
            #    stmt = stmt.limit(limit)

            return await self._list(s, stmt)

    async def get_by_id(self, item_id: int) -> Optional[Item]:
        """Объявление по ID"""
        async with self._sf() as s:
            return await s.get(Item, item_id)

    async def list_by_user_id(self, user_id: int, *, available_only: bool = False) -> List[Item]:
        """Все объявления владельца"""
        async with self._session() as s:
            stmt = select(Item).where(Item.user_id == user_id)
            if available_only:
                stmt = stmt.where(Item.is_available.is_(True))

            return await self._list(s, stmt)

    async def list_by_category(self, category_id: int, *, available_only: bool = True) -> List[Item]:
        """Получает все доступные объявления по категории"""
        async with self._session() as s:
            stmt = select(Item).where(Item.category_id == category_id)
            if available_only:
                stmt = self._apply_available_active_filter(stmt)

            return await self._list(s, stmt)

    async def list_by_subcategory(self, subcategory_id: int, *, available_only: bool = True) -> List[Item]:
        """Получает все доступные объявления по подкатегории"""
        async with self._session() as s:
            stmt = select(Item).where(Item.subcategory_id == subcategory_id)
            if available_only:
                stmt = self._apply_available_active_filter(stmt)

            return await self._list(s, stmt)

    async def search(self, query: str, *, available_only: bool = True, limit: int = 50, offset: int = 0) -> List[Item]:
        """Поиск объявлений по тексту. По названию ИЛИ описанию"""
        q = f"%{query.strip()}%"
        async with self._session() as s:
            stmt = select(Item).where(or_(Item.title.ilike(q), Item.description.ilike(q)))
            if available_only:
                stmt = self._apply_available_active_filter(stmt)
            stmt = stmt.limit(limit).offset(offset)

            return await self._list(s, stmt)

    # ──────────────────────────────────────────── NEW (Admin-Item logic) ────────────────────────────────────────

    async def list_by_status(self, status: ItemStatus, limit: int, offset: int = 0) -> List[Item]:
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

    async def list_pending(self, limit: int, offset: int = 0) -> List[Item]:
        """Объявления на модерации - PENDING"""
        return await self.list_by_status(status=ItemStatus.PENDING, limit=limit, offset=offset)


    async def set_status(self,
        item_id: int,
        new_status: ItemStatus,
        admin_id: int,
        reason: Optional[str] = None,
    ) -> Optional[Item]:
        """Техническое обновление статуса объявления. Бизнес-проверки выполняет сервис (whitelist)."""
        async with self._session() as s:
            obj: Optional[Item] = await s.get(Item, item_id)
            if not obj:
                return None

            obj.status = new_status
            obj.moderated_at = datetime.now(timezone.utc)
            obj.moderated_by_admin_id = admin_id
            if reason is not None:
                obj.moderation_reason = reason

            return await self._commit_refresh(s, obj)

    # ───────────────────────────────────────────────────────────────────────────────────────────────────────

    async def create(self,  user_id: int, item_data: ItemCreate) -> Optional[Item]:
        """Создать объявление"""
        obj = Item(user_id=user_id, **item_data.model_dump())
        async with self._session() as s:
            return await self._add_commit_refresh(s, obj)

    async def update(self, item_id: int,  update_data: ItemUpdate) -> Optional[Item]:
        """Обновить поля объявления (только переданные)"""
        async with self._session() as s:
            obj: Optional[Item] = await s.get(Item, item_id)
            if not obj:
                return None

            data = update_data.model_dump(exclude_unset=True)
            for k, v in data.items():
                setattr(obj, k, v)

            return await self._commit_refresh(s, obj)

    async def delete(self, item_id: int) -> bool:
        """Удалить объявление. True — удалено, False — не найдено/ошибка."""
        async with self._session() as s:
            obj = await s.get(Item, item_id)
            if not obj:
                return False

            return await self._delete_commit(s, obj)

    # ───────────────────────────────────────────────────────────────────────────────────────────────────────
    @staticmethod
    def _apply_available_active_filter(stmt):
        return (
            stmt.where(Item.is_available.is_(True))
            .where(Item.status == ItemStatus.ACTIVE) # NEW (Admin logic)
        )
        # stmt = stmt.where(Item.is_available.is_(True))
        # stmt = stmt.where(Item.status == ItemStatus.ACTIVE)