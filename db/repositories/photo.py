from __future__ import annotations

from typing import Callable, List, Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.photo import Photo


class PhotoRepository:
    """Репозиторий для работы с фотографиями"""

    def __init__(self, session_factory: Callable[[], AsyncSession]) -> None:
        self._sf = session_factory

    async def get_by_id(self, photo_id: int) -> Optional[Photo]:
        """Получить фото по ID"""
        async with self._sf() as s:
            return await s.get(Photo, photo_id)

    async def list_by_item_id(self, item_id: int) -> List[Photo]:
        """Все фото для конкретного объявления"""
        async with self._sf() as s:
            #stmt = select(Photo).where(Photo.item_id == item_id).order_by(Photo.order)
            stmt = (
                select(Photo)
                .where(Photo.item_id == item_id)
                .order_by(Photo.order.asc(), Photo.id.asc()) # Зачем сортировать ещё и по id?
            )
            res = await s.execute(stmt)
            return list(res.scalars())

    async def count_by_item(self, item_id: int) -> int:
        """Сколько фото привязано к объявлению"""
        async with self._sf() as s:
            stmt = select(func.count()).where(Photo.item_id == item_id)
            #stmt = select(func.count()).select_from(Photo).where(Photo.item_id == item_id)
            res = await s.execute(stmt)
            return res.scalar() or 0

    async def create(self, *, item_id: int, telegram_file_id: str, order: int = 0) -> Photo:
        """Создать фотографию для объявления"""
        async with self._sf() as s:
            obj = Photo(item_id=item_id, telegram_file_id=telegram_file_id, order=order)

            s.add(obj)
            try:
                await s.commit()
            except Exception:
                await s.rollback()
                raise
            await s.refresh(obj)
            return obj

    async def delete(self, photo_id: int) -> int:
        """Удалить фото по id. Возвращает True - если удалено, False - если не найдено"""
        async with self._sf() as s:
            obj = await s.get(Photo, photo_id)
            if not obj:
                return False

            await s.delete(obj)
            try:
                await s.commit()
            except Exception:
                await s.rollback()
                raise
            return True

    # --------------------------------------------------------------
    async def reorder(self, item_id: int):
        """Перенумеровать order = 0,.., N после удаления/добавления.
        Чтобы порядок был всегда плотным."""
        async with self._sf() as s:
            stmt = (
                select(Photo)
                .where(Photo.item_id == item_id)
                .order_by(Photo.order.asc(), Photo.id.asc())
            )
            result = await s.execute(stmt)
            photos = list(result.scalars())

            for i, photo in enumerate(photos):
                photo.order = i

            try:
                await s.commit()

            except Exception:
                await s.rollback()
                raise

            return len(photos)