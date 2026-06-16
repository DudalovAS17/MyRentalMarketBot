from typing import Optional, Literal
from sqlalchemy import select, func

from db.models.photo import Photo
from db.repositories.base import BaseRepository
from schemas.photo import PhotoCreate, PhotoUpdate

class PhotoRepository(BaseRepository):
    """Репозиторий фотографий товаров каталога."""

    # ───────────────────────────────────────────────────────────────────────────────────────────────────────
    @staticmethod
    def _apply_item_filter(stmt, item_id: int):
        """Оставить только фотографии товара."""
        return stmt.where(Photo.item_id == item_id)

    @staticmethod
    def _apply_order(stmt):
        """Стабильный порядок фотографий внутри карточки товара."""
        return stmt.order_by(Photo.sort_order.asc(), Photo.id.asc())

    @staticmethod
    def _apply_main_filter(stmt):
        """Оставить только главные фотографии."""
        return stmt.where(Photo.is_main.is_(True))

    async def _photos_in_order(self, session, item_id: int) -> list[Photo]:
        stmt = select(Photo)
        stmt = self._apply_item_filter(stmt, item_id)
        stmt = self._apply_order(stmt)
        result = await session.execute(stmt)
        return list(result.scalars())

    # ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    async def get_by_id(self, photo_id: int) -> Optional[Photo]:
        """Получить фото по ID"""
        async with self._session() as s:
            return await s.get(Photo, photo_id)

    async def list_by_item_id(self, item_id: int) -> list[Photo]:
        """Вернуть все фотографии товара."""
        async with self._session() as s:
            stmt = select(Photo)
            stmt = self._apply_item_filter(stmt, item_id)
            stmt = self._apply_order(stmt)
            return await self._list(s, stmt)

    async def get_main_by_item_id(self, item_id: int) -> Optional[Photo]:
        """Вернуть главную фотографию товара, если она задана."""
        async with self._session() as s:
            stmt = select(Photo)
            stmt = self._apply_item_filter(stmt, item_id)
            stmt = self._apply_main_filter(stmt)
            stmt = self._apply_order(stmt)
            return await self._one_or_none(s, stmt.limit(1))

    async def count_by_item(self, item_id: int) -> int:
        """Вернуть количество фотографий товара."""
        async with self._session() as s:
            stmt = select(func.count()).select_from(Photo)
            stmt = self._apply_item_filter(stmt, item_id)
            res = await s.execute(stmt)
            return int(res.scalar() or 0)

    # ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    async def create(self, photo_data: PhotoCreate) -> Photo:
        """Создать фотографию товара каталога."""
        async with self._session() as s:
            obj = Photo(**photo_data.model_dump())
            return await self._add_commit_refresh(s, obj)

    async def update(self, photo_id: int, update_data: PhotoUpdate) -> Optional[Photo]:
        """Обновить фотографию товара каталога."""
        async with self._session() as s:
            obj: Optional[Photo] = await s.get(Photo, photo_id)
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

            return await self._commit_refresh(s, obj)

    async def delete(self, photo_id: int) -> bool:
        """Удалить фото по id. Возвращает True - если удалено, False - если не найдено"""
        async with self._session() as s:
            obj = await s.get(Photo, photo_id)
            if not obj:
                return False

            return await self._delete_commit(s, obj)

    async def create_many(self, photos_data: list[PhotoCreate]) -> list[Photo]:
        """Создать несколько фотографий товара каталога за один commit."""
        if not photos_data:
            return []

        async with self._session() as s:
            photos = [Photo(**photo_data.model_dump()) for photo_data in photos_data]
            s.add_all(photos)
            await self._commit_or_rollback(s)
            for photo in photos:
                await s.refresh(photo)
            return photos

    # ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    async def reorder(self, item_id: int) -> int:
        """Уплотнить sort_order фотографий товара до 0..N."""
        async with self._session() as s:
            photos = await self._photos_in_order(s, item_id)
            if not photos:
                return 0

            for sort_order, photo in enumerate(photos):
                photo.sort_order = sort_order

            await self._commit_or_rollback(s)
            return len(photos)

    async def set_main(self, *, item_id: int, photo_id: int) -> bool:
        """Сделать фотографию главной внутри товара."""
        async with self._session() as s:
            photos = await self._photos_in_order(s, item_id) # Берёт все фото товара
            if photo_id not in {photo.id for photo in photos}: # Проверяет, что photo_id действительно принадлежит этому item_id
                return False

            for photo in photos:
                photo.is_main = photo.id == photo_id # Одну фотку делает главной

            await self._commit_or_rollback(s)
            return True

    async def swap_with_neighbor(self, *, item_id: int, photo_id: int, direction: Literal["up", "down"]) -> bool:
        """Поменять фотографию местами с соседней в пределах товара.

        True — swap выполнен, False — нельзя выполнить"""
        async with self._session() as s:
            photos = await self._photos_in_order(s, item_id) # Берёт все фото товара в текущем порядке
            photo_ids = [photo.id for photo in photos]
            if photo_id not in photo_ids: # Проверяет, что photo_id принадлежит этому item_id
                return False

            # [(10, 0), (11, 1), (12, 2)] (это для трех фото с id=10-12)
            # ids - [10, 11, 12], orders - [0, 1, 2]
            idx = photo_ids.index(photo_id) # поиск позиции переданного фото photo_id в списке
            # if photo_id=12 -> idx = 2 (index - ищет первое вхождение элемента (в ids) и возвращает его позицию (индекс))

            if direction == "up":
                if idx == 0: # уже самое верхнее, двигать некуда
                    return False
                swap_idx = idx - 1
            else: # down
                if idx == len(photos) - 1: # уже самое нижнее
                    return False
                swap_idx = idx + 1

            photos[idx], photos[swap_idx] = photos[swap_idx], photos[idx] # Меняет фото местами?
            for sort_order, photo in enumerate(photos):
                photo.sort_order = sort_order # Перезаписывает sort_order заново: 0, 1, 2, ...

            await self._commit_or_rollback(s)
            return True

    async def set_order(self, *, photo_id: int, item_id: int, new_order: int) -> bool:
        """Установить позицию фотографии внутри списка фотографий товара."""
        async with self._session() as s:
            photos = await self._photos_in_order(s, item_id)
            photo_ids = [photo.id for photo in photos]
            if photo_id not in photo_ids:
                return False

            if new_order < 0 or new_order >= len(photos):
                return False

            # достали нужное фото и вставили в новую позицию
            current_index = photo_ids.index(photo_id)
            if current_index == new_order: # ранний выход, если фото уже стоит на нужной позиции
                return True
            photo = photos.pop(current_index)
            photos.insert(new_order, photo)

            # после перестановки порядок всегда становится плотным: 0, 1, 2, 3...
            for sort_order, photo in enumerate(photos):
                photo.sort_order = sort_order

            await self._commit_or_rollback(s)
            return True