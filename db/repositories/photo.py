import logging
from typing import Callable, List, Optional

from sqlalchemy import select, delete, func
from sqlalchemy.util import await_only
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.photo import Photo

logger = logging.getLogger(__name__)


class PhotoRepository:
    """Репозиторий для работы с фотографиями"""

    def __init__(self, session_factory: Callable[[], AsyncSession]) -> None:
        self._sf = session_factory

    async def get_by_id(self, photo_id: int) -> Optional[Photo]:
        """Получить фото по ID"""
        async with self._sf() as s:
            return await s.get(Photo, photo_id)

    async def get_by_item_id(self, item_id: int) -> List[Photo]:
        """Все фото для конкретного объявления"""
        async with self._sf() as s:
            #stmt = select(Photo).where(Photo.item_id == item_id).order_by(Photo.order)
            stmt = (
                select(Photo)
                .where(Photo.item_id == item_id)
                .order_by(Photo.order.asc(), Photo.id.asc()) # Зачем сортировать ещё и по id?
                # Каждое фото имеет уникальный id — значит, даже если order = 0 у двух фото, порядок всё равно будет строгим.
                # 1) id=5 (order=0)
                # 2) id=12 (order=0)
                # 3) id=9 (order=1)
            )
            res = await s.execute(stmt)
            return list(res.scalars().all())

    async def count_by_item(self, item_id: int) -> int:
        """Сколько фото привязано к объявлению"""
        async with self._sf() as s:
            stmt = select(func.count()).where(Photo.item_id == item_id)
            res = await s.execute(stmt)
            return res.scalar() or 0

    async def create(self, *, item_id: int, telegram_file_id: str, order: int = 0) -> Photo:
        """Создать фотографию для объявления"""
        async with self._sf() as s:
            obj = Photo(item_id=item_id, telegram_file_id=telegram_file_id, order=order)
            try:
                s.add(obj)
                await s.commit()
                await s.refresh(obj)
                logger.info("create() — фото добавлено для item_id=%s", item_id)
                return obj
            except Exception as e:
                await s.rollback()
                logger.error("create() — ошибка при добавлении фото: %s", e, exc_info=True)
                raise

    # возможно перейти на begin():
    """
    async def create(
        self, *, item_id: int, telegram_file_id: str, order: int = 0
    ) -> Photo:
        async with self._sf() as s:
            async with s.begin():
                obj = Photo(
                    item_id=item_id,
                    telegram_file_id=telegram_file_id,
                    order=order,
                )
                s.add(obj)
            await s.refresh(obj)
            return obj
    """

    async def delete(self, photo_id: int) -> int:
        """Удалить фото по id. Возвращает 1 если удалено, 0 если не найдено"""
        async with self._sf() as s:
            obj = await s.get(Photo, photo_id)
            if not obj:
                logger.warning("delete() — фото id=%s не найдено", photo_id)
                return 0
            await s.delete(obj)
            try:
                await s.commit()
                logger.info("delete() — фото id=%s удалено", photo_id)
                return 1
            except Exception as e:
                await s.rollback()
                logger.error("delete() — ошибка при удалении фото id=%s: %s", photo_id, e, exc_info=True)
                raise

    """
    async def delete_all_for_item(self, item_id: int) -> int:
        ""Удалить все фото товара — полезно при полном удалении объявления""
        async with self._sf() as s:
            async with s.begin():
                stmt = delete(Photo).where(Photo.item_id == item_id)
                res = await s.execute(stmt)
                return res.rowcount or 0
    """

    async def reorder(self, item_id: int):
        """Перенумеровать order = 0..N после удаления/добавления.
        Чтобы порядок был всегда плотным."""
        async with self._sf() as s:
            async with s.begin():
                stmt = (
                    select(Photo)
                    .where(Photo.item_id == item_id)
                    .order_by(Photo.order.asc(), Photo.id.asc())
                )
                result = await s.execute(stmt)
                photos = list(result.scalars().all())

                for i, photo in enumerate(photos):
                    photo.order = i
