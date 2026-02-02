from __future__ import annotations
from typing import Callable, Optional, List #, Dict, Any
#from decimal import Decimal

import logging
from sqlalchemy import select, or_, exists, and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
#from sqlalchemy.sql import func
from datetime import datetime, timezone

from db.models.item import Item
from db.models.rental import Rental, RentalStatus
from schemas.item import ItemCreate, ItemUpdate

from utils.item_status import can_transition
from utils.rental_status import is_open_status

logger = logging.getLogger(__name__)


class ItemRepository:
    """Репозиторий объявлений. DI: session_factory -> Session."""

    def __init__(self, session_factory: Callable[[], AsyncSession]) -> None:
        self._sf = session_factory

    # ──────────────────────────────────────────────────────────────────

    async def get_all(self, *, available_only: bool = True, limit: Optional[int] = None, offset: int = 0) -> List[Item]:
        """Все объявления (по умолчанию только доступные)"""
        async with self._sf() as s:
            stmt = select(Item)
            if available_only:
                stmt = stmt.where(Item.is_available.is_(True))
                stmt = stmt.where(Item.status == "ACTIVE") # NEW (Admin logic)
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
                stmt = stmt.where(Item.status == "ACTIVE") # NEW (Admin logic)
            res = await s.execute(stmt)
            return list(res.scalars())
        # logger.error(f"[ItemRepository] Ошибка при получении объявлений категории {category_id}: {e}", exc_info=True)

    async def get_by_subcategory(self, subcategory_id: int, *, available_only: bool = True) -> List[Item]:
        """Получает все доступные объявления по подкатегории"""
        async with self._sf() as s:
            stmt = select(Item).where(Item.subcategory_id == subcategory_id)
            if available_only:
                stmt = stmt.where(Item.is_available.is_(True))
                stmt = stmt.where(Item.status == "ACTIVE") # NEW (Admin logic)
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
                stmt = stmt.where(Item.status == "ACTIVE")  # NEW (Admin logic)
            stmt = stmt.limit(limit).offset(offset)
            res = await s.execute(stmt)
            return list(res.scalars().all()) # .all()

    # ──────────────────────────────────────────── NEW (Admin-Item logic) ────────────────────────────────────────

    async def list_pending(self, limit: int, offset: int = 0) -> List[Item]:
        """Объявления на модерации - PENDING"""
        return await self.list_by_status(status="PENDING", limit=limit, offset=offset)

    async def list_by_status(self, status: str, limit: int, offset: int = 0) -> List[Item]:
        """Объявления на модерации по статусу, по убыванию id"""
        async with self._sf() as s:
            stmt = (
                select(Item)
                .where(Item.status == status)
                .order_by(Item.id.desc()) # по убыванию id ?
                .limit(limit)
                .offset(offset)
            )
            res = await s.execute(stmt)
            return list(res.scalars().all())

    async def set_status_with_whitelist(
        self,
        item_id: int,
        new_status: str,
        admin_id: int,
        reason: Optional[str] = None,
    ) -> Optional[Item]:
        """Обновить статус с проверкой whitelist переходов."""
        async with self._sf() as s:
            obj: Optional[Item] = await s.get(Item, item_id)
            # : Optional[Item] чтобы return obj не подчеркивалось, так он понимает ясно что это
            if not obj:
                logger.warning("Объявление с id=%s не найдено для модерации", item_id)
                return None

            old_status = str(obj.status)

            if not can_transition(old_status, new_status):
                logger.warning(
                    "Нельзя сменить статус объявления id=%s: %s -> %s",
                    item_id,
                    obj.status,
                    new_status,
                )
                return None

            # Есть открытые сделки - нельзя скрыть объявление!
            # ТОЛЬКО при скрытии объявления возникает риск сломать активную сделку, поэтому
            if new_status == "HIDDEN": # (отклонено админом)
                # Считаем "open" статусы сделок:
                #open_statuses = [status for status in RentalStatus if is_open_status(status)]
                open_statuses = []
                for st in RentalStatus:
                    if is_open_status(st):
                        open_statuses.append(getattr(st, "value", st))
                # если Rental.status хранится как строка → делай status.value
                # если хранится как Enum → оставляй Enum

                has_open_rentals_stmt = select(
                    exists().where(
                        and_(
                            Rental.item_id == item_id,
                            Rental.status.in_(open_statuses),
                        )
                    )
                )
                has_open_rentals = bool(await s.scalar(has_open_rentals_stmt))
                if has_open_rentals:
                    logger.warning(
                        "Нельзя скрыть объявление id=%s: есть открытые сделки",
                        item_id,
                    )
                    return None
            """ if new_status == "HIDDEN"
                Если не поставить guard, получится:
                    - сделка продолжается
                    - объявление скрыто
                    - пользователь:
                        не видит свой item в каталоге
                        может потерять доступ к контексту сделки
                    - админ:
                        нарушил целостность модели “item ↔ deal”
            
                Почему НЕ проверяем другие статусы
                ❌ new_status == "ACTIVE"
                    при активации объявления:                
                        мы не ломаем сделки                
                        наоборот, разрешаем рынок                
                    нет риска консистентности                
                ❌ new_status == "REJECTED"                
                    REJECTED применяется только из PENDING               
                    по PENDING физически не может быть сделок                
                    guard не нужен                
                ❌ new_status == "PENDING"                
                    админ туда не переводит                
                    пользовательских переходов тут нет
            """

            obj.status = new_status
            obj.moderated_at = datetime.now(timezone.utc) # func.now()
            obj.moderated_by_admin_id = admin_id
            if reason is not None:
                obj.moderation_reason = reason

            try:
                await s.commit()
            except IntegrityError as e:
                await s.rollback()
                logger.error("item moderation update failed (id=%s): %s", item_id, e, exc_info=True)
                return None

            await s.refresh(obj)
            logger.info("item status updated id=%s status=%s", obj.id, obj.status)
            return obj

    # ───────────────────────────────────────────────────────────────────────────────────────────────────────

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
