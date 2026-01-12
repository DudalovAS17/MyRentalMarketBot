from __future__ import annotations
from typing import Callable, Optional, List #, Dict, Any
#from decimal import Decimal

import logging
from sqlalchemy import select, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.item import Item
from schemas.item import ItemCreate, ItemUpdate

logger = logging.getLogger(__name__)


class ItemRepository:
    """Репозиторий объявлений. DI: session_factory -> Session."""

    def __init__(self, session_factory: Callable[[], AsyncSession]) -> None:
        self._sf = session_factory

    # ── READ ────────────────────────────────────────────────────────────────

    async def get_all(self, *, available_only: bool = True, limit: Optional[int] = None, offset: int = 0) -> List[Item]:
        """Все объявления (по умолчанию только доступные)"""
        async with self._sf() as s:
            stmt = select(Item)
            if available_only:
                stmt = stmt.where(Item.is_available.is_(True))
            if limit is not None:
                stmt = stmt.limit(limit).offset(offset)
                # limit - возьми не больше n строк
                # offset - пропусти k первых строк и начинай отдавать дальше
            res = await s.execute(stmt)
            return list(res.scalars())
        # logger.error(f"[ItemRepository] Ошибка при получении всех объявлений: {e}")

    async def get_by_id(self, item_id: int) -> Optional[Item]:
        """Объявление по ID"""
        async with self._sf() as s:
            return await s.get(Item, item_id)
        # logger.error(f"[ItemRepository] Ошибка при получении объявления {item_id}: {e}")

    async def get_by_user_id(self, user_id: int, *, available_only: bool = False) -> List[Item]:
        """Объявления владельца"""
        async with self._sf() as s:
            stmt = select(Item).where(Item.user_id == user_id)
            if available_only:
                stmt = stmt.where(Item.is_available.is_(True))
            res = await s.execute(stmt)
            return list(res.scalars().all()) # .all()

    async def get_by_category(self, category_id: int, *, available_only: bool = True) -> List[Item]:
        """Получает все доступные объявления по категории"""
        async with self._sf() as s:
            stmt = select(Item).where(Item.category_id == category_id)
            if available_only:
                stmt = stmt.where(Item.is_available.is_(True))
            res = await s.execute(stmt)
            return list(res.scalars())
        # logger.error(f"[ItemRepository] Ошибка при получении объявлений категории {category_id}: {e}", exc_info=True)

    async def get_by_subcategory(self, subcategory_id: int, *, available_only: bool = True) -> List[Item]:
        """Получает все доступные объявления по подкатегории"""
        async with self._sf() as s:
            stmt = select(Item).where(Item.subcategory_id == subcategory_id)
            if available_only:
                stmt = stmt.where(Item.is_available.is_(True))
            res = await s.execute(stmt)
            return list(res.scalars().all()) # .all()

    async def search(self, query: str, *, available_only: bool = True, limit: int = 50, offset: int = 0) -> List[Item]:
        """Поиск объявлений по тексту. По названию ИЛИ описанию"""
        q = f"%{query.strip()}%"
        async with self._sf() as s:
            stmt = select(Item).where(or_(Item.title.ilike(q), Item.description.ilike(q))) # По названию ИЛИ описанию
            # Примеры: "ноут" найдёт и "Ноутбук", и "НОУТ"
            if available_only:
                stmt = stmt.where(Item.is_available.is_(True))
            stmt = stmt.limit(limit).offset(offset)
            res = await s.execute(stmt)
            return list(res.scalars().all()) # .all()

    # ── WRITE ───────────────────────────────────────────────────────────────

    async def create(self, item_data: ItemCreate) -> Optional[Item]:
        """Создать объявление"""
        obj = Item(**item_data.model_dump())  # фото отдельно
        async with self._sf() as s: # s - session
            s.add(obj)
            try:
                await s.commit()
            except IntegrityError as e:
                await s.rollback()
                logger.error("Ошибка при создании объявления: %s", e, exc_info=True)
                raise
            await s.refresh(obj)  # чтобы были server defaults (id/created_at/updated_at)
            logger.info("item created id=%s user_id=%s title=%r", obj.id, obj.user_id, obj.title)
            return obj

    async def update(self, item_id: int,  update_data: ItemUpdate) -> Optional[Item]:
        """Обновить поля объявления (только переданные)"""
        async with self._sf() as s:
            obj = await s.get(Item, item_id)
            if not obj:
                logger.warning("Объявление с id=%s не найдено для обновления", item_id)
                return None

            data = update_data.model_dump(exclude_unset=True)
            # ✅ exclude_unset=True — вернёт только реально переданные поля (удобно для update)
            for k, v in data.items(): # data.items() возвращает пары ключ-значение
                # ("title", "Новая палатка"), ("price", 2500)
                setattr(obj, k, v) # Это аналог:  obj.title = "Новая палатка"   obj.price = 2500
            # Но мы делаем это в цикле для любого набора полей

            """
            changed = False
            def set_if_changed(attr: str, value):
                nonlocal changed # даём функции доступ к флагу changed из внешней области
                if value is None:
                    return
                cur = getattr(obj, attr) # текущее значение поля на объекте
                new = value.strip() if isinstance(value, str) else value
                if new != cur:
                    setattr(obj, attr, new)
                    changed = True # мы реально что-то поменяли

            set_if_changed("title", title)
            set_if_changed("description", description)
            set_if_changed("price", price)
            set_if_changed("deposit", deposit)
            set_if_changed("min_rental_period", min_rental_period)
            set_if_changed("max_rental_period", max_rental_period)
            set_if_changed("location", location)
            set_if_changed("coordinates", coordinates)
            set_if_changed("is_available", is_available)
            set_if_changed("is_featured", is_featured)
            set_if_changed("category_id", category_id)
            set_if_changed("subcategory_id", subcategory_id)

            if not changed:
                return obj
                # заход в бд только если изменения есть
            """

            try:
                await s.commit()
            except IntegrityError as e:
                await s.rollback()
                logger.error("item update failed (id=%s): %s", item_id, e, exc_info=True)
                return None

            # если важны server defaults (updated_at), подтянем
            await s.refresh(obj)
            logger.info("item updated id=%s", obj.id)
            return obj

    async def delete(self, item_id: int) -> int:
        """Удалить объявление. 1 — удалено, 0 — не найдено/ошибка."""
        async with self._sf() as s:
            obj = await s.get(Item, item_id)
            if not obj:
                logger.info("item not found for delete (id=%s)", item_id)
                return 0
            await s.delete(obj)
            try:
                await s.commit()
            except IntegrityError as e:
                await s.rollback()
                logger.error("item delete failed (id=%s): %s", item_id, e, exc_info=True)
                return 0
            logger.info("item deleted id=%s", item_id)
            return 1
