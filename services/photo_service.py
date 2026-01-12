from typing import List, Optional

from db.repositories.photo import PhotoRepository
from schemas.photo import PhotoCreate, PhotoOut
from db.models.photo import Photo
from sqlalchemy.exc import SQLAlchemyError
import logging

logger = logging.getLogger(__name__)


class PhotoService:
    """Сервис для управления фотографиями объявления."""

    def __init__(self, photo_repo: PhotoRepository):
        self.photo_repo = photo_repo

    async def add_photo(self, *, item_id: int, telegram_file_id: str, order: Optional[int] = None) -> PhotoOut:
        """Добавляет фото к объявлению (если order не указан → ставим в конец)"""

        try:
            # если order не указан — нужно узнать текущий максимум
            if order is None:
                photos = await self.photo_repo.get_by_item_id(item_id)
                order = len(photos)

            new_photo = await self.photo_repo.create(
                item_id=item_id,
                telegram_file_id=telegram_file_id,
                order=order,
            )

            # После добавления перестраиваем порядок (без дырок)
            await self.photo_repo.reorder(item_id)

            return PhotoOut.model_validate(new_photo)

        except SQLAlchemyError as e:
            logger.error(f"[PhotoService.add_photo] Ошибка БД: {e}", exc_info=True)
            raise

    # работает, но не обдумывал
    async def add_photos(self, item_id: int, file_ids: list[str]) -> list[PhotoOut]:
        """Добавить несколько фотографий к объявлению.
        Порядок назначается «хвостом» после уже существующих.
        """
        if not file_ids:
            return []

        existing = await self.photo_repo.get_by_item_id(item_id)
        start_order = len(existing)

        result: list[PhotoOut] = []

        for offset, file_id in enumerate(file_ids):
            photo = await self.photo_repo.create(
                item_id=item_id,
                telegram_file_id=file_id,
                order=start_order + offset,
            )
            result.append(PhotoOut.model_validate(photo))

        # при желании можно вызвать reorder, но тут порядок и так плотный
        # await self.repo.reorder(item_id)

        return result

    async def get_photos(self, item_id: int) -> List[PhotoOut]:
        """Возвращает все фото объявления в правильном порядке."""
        photos = await self.photo_repo.get_by_item_id(item_id)
        return [PhotoOut.model_validate(p) for p in photos]

    async def get_photo(self, photo_id: int) -> Optional[PhotoOut]:
        """Получить одно фото."""
        photo = await self.photo_repo.get_by_id(photo_id)
        return PhotoOut.model_validate(photo) if photo else None


    async def delete_photo(self, photo_id: int) -> bool:
        """Удаляет фото и пересортировывает порядок."""
        try:
            photo = await self.photo_repo.get_by_id(photo_id)
            if not photo:
                return False

            item_id = photo.item_id

            deleted = await self.photo_repo.delete(photo_id)
            if not deleted:
                return False

            # Перестраиваем порядок у оставшихся
            await self.photo_repo.reorder(item_id)
            return True

        except SQLAlchemyError as e:
            logger.error(f"[PhotoService.delete_photo] Ошибка удаления: {e}", exc_info=True)
            raise


    async def move_photo(self, photo_id: int, direction: str) -> bool:
        """Перемещает фото вверх или вниз (direction: 'up' | 'down')"""

        photo = await self.photo_repo.get_by_id(photo_id)
        if not photo:
            return False

        photos = await self.photo_repo.get_by_item_id(photo.item_id)
        photos_sorted = sorted(photos, key=lambda p: p.order)

        idx = next((i for i, p in enumerate(photos_sorted) if p.id == photo_id), None)
        if idx is None:
            return False

        # swap with previous
        if direction == "up" and idx > 0:
            photos_sorted[idx].order, photos_sorted[idx - 1].order = (
                photos_sorted[idx - 1].order,
                photos_sorted[idx].order,
            )

        # swap with next
        elif direction == "down" and idx < len(photos_sorted) - 1:
            photos_sorted[idx].order, photos_sorted[idx + 1].order = (
                photos_sorted[idx + 1].order,
                photos_sorted[idx].order,
            )
        else:
            return False

        # сохраняем изменения
        async with self.photo_repo._sf() as s:
            async with s.begin():
                for p in photos_sorted:
                    s.add(p)

        # опять перестраиваем порядок, чтобы было 0,1,2,3
        await self.photo_repo.reorder(photo.item_id)

        return True

    async def set_order(self, photo_id: int, new_order: int) -> bool:
        """Установить явный order для фото."""
        photo = await self.photo_repo.get_by_id(photo_id)
        if not photo:
            return False

        photos = await self.photo_repo.get_by_item_id(photo.item_id)
        if new_order < 0 or new_order >= len(photos):
            return False

        # вставляем фото на позицию new_order
        photos_sorted = [p for p in photos if p.id != photo_id]
        photos_sorted.insert(new_order, photo)

        # сохраняем порядок
        async with self.photo_repo._sf() as s:
            async with s.begin():
                for i, p in enumerate(photos_sorted):
                    p.order = i
                    s.add(p)

        return True
