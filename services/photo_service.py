import logging
from typing import Optional, Literal

from db.repositories.photo import PhotoRepository

from schemas.photo import PhotoCreate, PhotoOut
from utils.errors import NotFoundError, ConflictError

logger = logging.getLogger(__name__)

class PhotoService:
    """Сервис для управления фотографиями товаров каталога."""

    def __init__(self, repo: PhotoRepository):
        self.repo = repo

    # ────────────────────────────────────────── DTO helpers ──────────────────────────────────────────────────────────
    @staticmethod
    def _to_out(photo) -> PhotoOut:
        return PhotoOut.model_validate(photo)

    @classmethod
    def _to_out_list(cls, photos) -> list[PhotoOut]:
        return [cls._to_out(photo) for photo in photos]

    # ────────────────────────────────────────── Read methods ──────────────────────────────────────────────────────────
    async def get_photos_by_item_id(self, item_id: int) -> list[PhotoOut]:
        """Возвращает все фото товара в правильном порядке."""
        photos = await self.repo.list_by_item_id(item_id)
        return self._to_out_list(photos)

    async def get_photo_by_id(self, photo_id: int, *, strict: bool = False) -> Optional[PhotoOut]:
        """Получить одно фото"""
        photo = await self.repo.get_by_id(photo_id)
        if not photo:
            if strict:
                raise NotFoundError(f"Фото не найдено: id={photo_id}")
            return None

        return self._to_out(photo)

    # ─────────────────────────────────────────── write methods ────────────────────────────────────────────────────────
    async def create_photo(self, *, item_id: int, telegram_file_id: str) -> PhotoOut:
        """Добавить фото к товару в конец списка."""

        current_count = await self.repo.count_by_item(item_id)

        photo_data = PhotoCreate(
            item_id=item_id,
            telegram_file_id=telegram_file_id,
            sort_order=current_count,
            is_main=current_count == 0,
        )
        new_photo = await self.repo.create(photo_data)

        dto = self._to_out(new_photo)
        logger.info("Фото id=%s добавлено к товару: item_id=%s", dto.id, item_id)
        return dto

    async def create_photos(self, item_id: int, file_ids: list[str]) -> list[PhotoOut]:
        """Добавить несколько фотографий в конец списка фотографий товара каталога."""
        if not file_ids:
            return []

        start_order = await self.repo.count_by_item(item_id)

        photos_data: list[PhotoCreate] = []
        for offset, file_id in enumerate(file_ids):
            photo_data = PhotoCreate(
                item_id=item_id,
                telegram_file_id=file_id,
                sort_order=start_order + offset,
                is_main=(start_order == 0 and offset == 0), # первое фото пачки становится главным только если до этого у товара не было фото
            )
            photos_data.append(photo_data)

        photos = await self.repo.create_many(photos_data)
        result = self._to_out_list(photos)

        logger.info("Фото (count=%s штук) добавлены к товару: item_id=%s", len(result), item_id)
        return result

    async def delete_photo(self, photo_id: int, *, strict: bool = False) -> bool:
        """Удалить фото и уплотнить порядок у оставшихся. True — удалено, False — иначе."""

        photo = await self.repo.get_by_id(photo_id)
        if not photo:
            if strict:
                raise NotFoundError(f"Фото не найдено: id={photo_id}")
            return False

        # удаляем фото
        deleted = await self.repo.delete(photo_id)
        if not deleted:
            if strict:
                raise NotFoundError(f"Фото не найдено: id={photo_id}")
            return False

        # уплотняем порядок
        await self.repo.reorder(photo.item_id)

        logger.info("Фото id=%s удалено из данного товара item_id=%s", photo_id, photo.item_id)
        return True
    # TODO: Сейчас если удалили главное фото (is_main=True), сервис не назначает новое главное фото.

    # ──────────────────────────────────────── Order management ────────────────────────────────────────────────────────
    async def move_photo(self, photo_id: int, direction: Literal["up", "down"], strict: bool = False) -> bool:
        """Перемещает фото вверх или вниз (direction: 'up' | 'down') внутри списка фотографий товара"""

        photo = await self.repo.get_by_id(photo_id)
        if not photo:
            if strict:
                raise NotFoundError(f"Фото не найдено: id={photo_id}")
            return False

        # repo должен найти соседа и сделать swap атомарно
        ok = await self.repo.swap_with_neighbor(item_id=photo.item_id, photo_id=photo_id, direction=direction)
        if not ok and strict:
            raise ConflictError("Нельзя переместить фото (уже крайнее или изменилось)")

        return ok

    async def set_order(self, photo_id: int, new_order: int, strict: bool = False) -> bool:
        """Установить новую позицию (sort_order) фотографии внутри списка фотографий товара"""
        photo = await self.repo.get_by_id(photo_id)
        if not photo:
            if strict:
                raise NotFoundError(f"Фото не найдено: id={photo_id}")
            return False

        ok = await self.repo.set_order(photo_id=photo_id, item_id=photo.item_id, new_order=new_order)

        if not ok and strict:
            raise ConflictError("Нельзя изменить порядок (позиция вне диапазона или данные изменились)")

        return ok