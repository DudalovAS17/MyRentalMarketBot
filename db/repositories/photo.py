from __future__ import annotations

from typing import Callable, List, Optional, Literal
from sqlalchemy import select, update, func, case
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
            return int(res.scalar() or 0)

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

    async def delete(self, photo_id: int) -> bool:
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


    # ────────────────────────────────────────────────────────────────────────────────────────────────────────
    # for move_photo() - ну "такая себе" функция, сойдет
    async def swap_with_neighbor(self, *, item_id: int, photo_id: int, direction: Literal["up", "down"]
    ) -> bool:
        """True — swap выполнен, False — нельзя выполнить"""
        async with self._sf() as s:
            # 1) получаем упорядоченный список id+order
            stmt = (
                select(Photo.id, Photo.order)
                .where(Photo.item_id == item_id)
                .order_by(Photo.order.asc(), Photo.id.asc())
            )
            res = await s.execute(stmt)
            rows = res.all() # [(10, 0), (11, 1), (12, 2)] (это для трех фото с id=10-12)
            if not rows:
                return False

            ids = [r[0] for r in rows] # [10, 11, 12]
            orders = [r[1] for r in rows] # [0, 1, 2]

            try:
                idx = ids.index(photo_id) # поиск позиции переданного фото photo_id в списке
                # if photo_id=12 -> idx = 2 (index - ищет первое вхождение элемента (в ids) и возвращает его позицию (индекс))
            except ValueError: # ?
                return False

            if direction == "up":
                if idx == 0: # уже самое верхнее, двигать некуда
                    return False
                other_id, other_order = ids[idx - 1], orders[idx - 1]
            else:  # down
                if idx == len(ids) - 1: # уже самое нижнее
                    return False
                other_id, other_order = ids[idx + 1], orders[idx + 1]

            this_order = orders[idx] # order текущего

            # 2) делаем swap двух строк в одной транзакции
            try:
                async with s.begin():
                    await s.execute(update(Photo).where(Photo.id == photo_id).values(order=other_order))
                    await s.execute(update(Photo).where(Photo.id == other_id).values(order=this_order))
            except Exception:
                await s.rollback()
                raise

            return True

    # for set_order() - ну "такая себе" функция, сойдет
    async def set_order(self, *, photo_id: int, item_id: int, new_order: int) -> bool:
        async with self._sf() as s:
            photos = list(
                    (
                        await s.execute(
                            select(Photo.id)
                            .where(Photo.item_id == item_id)
                            .order_by(Photo.order.asc(), Photo.id.asc())
                        )
                    ).scalars().all()
            )

            if photo_id not in photos:
                return False

            n = len(photos)
            if new_order < 0 or new_order >= n:
                return False

            # переставляем photo_id в нужную позицию
            photos.remove(photo_id)
            photos.insert(new_order, photo_id)

            # обновляем order всем одним UPDATE через CASE (быстро, без цикла add())
            mapping = {pid: idx for idx, pid in enumerate(photos)}
            stmt = (
                update(Photo)
                .where(Photo.item_id == item_id)
                .values(order=case(mapping, value=Photo.id))
            )

            async with s.begin():
                await s.execute(stmt)

            return True