from __future__ import annotations

from typing import Callable, Optional, List
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from db.models.item import Item
from schemas.item import ItemCreate, ItemUpdate

from utils.item_status import ItemStatus


class ItemRepository:
    """Репозиторий объявлений"""

    def __init__(self, session_factory: Callable[[], AsyncSession]) -> None:
        self._sf = session_factory

    # ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    async def list_all(self, *, available_only: bool = True, limit: Optional[int] = None, offset: int = 0) -> List[Item]:
        """Все объявления (по умолчанию только доступные)"""
        async with self._sf() as s:
            stmt = select(Item)
            if available_only:
                stmt = stmt.where(Item.is_available.is_(True))
                stmt = stmt.where(Item.status == ItemStatus.ACTIVE) # NEW (Admin logic)

            if limit is not None:
                stmt = stmt.limit(limit).offset(offset)
            #stmt = stmt.offset(offset)
            #if limit is not None:
            #    stmt = stmt.limit(limit)

            res = await s.execute(stmt)
            return list(res.scalars())

    async def get_by_id(self, item_id: int) -> Optional[Item]:
        """Объявление по ID"""
        async with self._sf() as s:
            return await s.get(Item, item_id)

    async def list_by_user_id(self, user_id: int, *, available_only: bool = False) -> List[Item]:
        """Все объявления владельца"""
        async with self._sf() as s:
            stmt = select(Item).where(Item.user_id == user_id)
            if available_only:
                stmt = stmt.where(Item.is_available.is_(True))

            res = await s.execute(stmt)
            return list(res.scalars())

    async def list_by_category(self, category_id: int, *, available_only: bool = True) -> List[Item]:
        """Получает все доступные объявления по категории"""
        async with self._sf() as s:
            stmt = select(Item).where(Item.category_id == category_id)
            if available_only:
                stmt = stmt.where(Item.is_available.is_(True))
                stmt = stmt.where(Item.status == ItemStatus.ACTIVE) # NEW (Admin logic)

            res = await s.execute(stmt)
            return list(res.scalars())

    async def list_by_subcategory(self, subcategory_id: int, *, available_only: bool = True) -> List[Item]:
        """Получает все доступные объявления по подкатегории"""
        async with self._sf() as s:
            stmt = select(Item).where(Item.subcategory_id == subcategory_id)
            if available_only:
                stmt = stmt.where(Item.is_available.is_(True))
                stmt = stmt.where(Item.status == ItemStatus.ACTIVE) # NEW (Admin logic)

            res = await s.execute(stmt)
            return list(res.scalars())

    async def search(self, query: str, *, available_only: bool = True, limit: int = 50, offset: int = 0) -> List[Item]:
        """Поиск объявлений по тексту. По названию ИЛИ описанию"""
        q = f"%{query.strip()}%"
        async with self._sf() as s:
            stmt = select(Item).where(or_(Item.title.ilike(q), Item.description.ilike(q)))
            if available_only:
                stmt = stmt.where(Item.is_available.is_(True))
                stmt = stmt.where(Item.status == ItemStatus.ACTIVE)  # NEW (Admin logic)
            stmt = stmt.limit(limit).offset(offset)

            res = await s.execute(stmt)
            return list(res.scalars())

    # ──────────────────────────────────────────── NEW (Admin-Item logic) ────────────────────────────────────────

    async def list_by_status(self, status: ItemStatus, limit: int, offset: int = 0) -> List[Item]:
        """Объявления на модерации по статусу, по убыванию id"""
        async with self._sf() as s:
            stmt = (
                select(Item)
                .where(Item.status == status)
                .order_by(Item.id.desc())
                .limit(limit)
                .offset(offset)
            )

            res = await s.execute(stmt)
            return list(res.scalars().all())

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
        async with self._sf() as s:
            obj: Optional[Item] = await s.get(Item, item_id)
            if not obj:
                return None

            obj.status = new_status
            obj.moderated_at = datetime.now(timezone.utc)
            obj.moderated_by_admin_id = admin_id
            if reason is not None:
                obj.moderation_reason = reason

            try:
                await s.commit()
            except Exception:
                await s.rollback()
                raise

            await s.refresh(obj)
            return obj

    # ───────────────────────────────────────────────────────────────────────────────────────────────────────

    async def create(self, item_data: ItemCreate) -> Optional[Item]:
        """Создать объявление"""
        obj = Item(**item_data.model_dump())
        async with self._sf() as s:
            s.add(obj)
            try:
                await s.commit()
            except Exception:
                await s.rollback()
                raise
            await s.refresh(obj)
            return obj

    async def update(self, item_id: int,  update_data: ItemUpdate) -> Optional[Item]:
        """Обновить поля объявления (только переданные)"""
        async with self._sf() as s:
            obj: Optional[Item] = await s.get(Item, item_id)
            if not obj:
                return None

            data = update_data.model_dump(exclude_unset=True)
            for k, v in data.items():
                setattr(obj, k, v)

            try:
                await s.commit()
            except Exception:
                await s.rollback()
                raise
            await s.refresh(obj)
            return obj

    async def delete(self, item_id: int) -> bool:
        """Удалить объявление. True — удалено, False — не найдено/ошибка."""
        async with self._sf() as s:
            obj = await s.get(Item, item_id)
            if not obj:
                return False
            await s.delete(obj)
            try:
                await s.commit()
            except Exception:
                await s.rollback()
                raise
            return True

    # ───────────────────────────────────────────────────────────────────────────────────────────────────────