import logging
from typing import Optional, Literal

from db.repositories.photo import PhotoRepository
from schemas.photo import PhotoOut
from utils.errors import NotFoundError, ConflictError

logger = logging.getLogger(__name__)

class PhotoService:
    """Сервис для управления фотографиями объявления."""

    def __init__(self, photo_repo: PhotoRepository):
        self.photo_repo = photo_repo

    async def get_photos(self, item_id: int) -> list[PhotoOut]:
        """Возвращает все фото объявления в правильном порядке."""
        photos = await self.photo_repo.list_by_item_id(item_id)
        return [PhotoOut.model_validate(p) for p in photos]

    async def get_photo(self, photo_id: int, *, strict: bool = False) -> Optional[PhotoOut]:
        """Получить одно фото"""
        photo = await self.photo_repo.get_by_id(photo_id)
        if not photo:
            if strict:
                raise NotFoundError(f"Фото не найдено: id={photo_id}")
            return None

        return PhotoOut.model_validate(photo)

    # -------------------------------------------------------------------------------------------------------
    async def add_photo(self, *, item_id: int, telegram_file_id: str, order: Optional[int] = None) -> PhotoOut:
        """Добавляет фото к объявлению (если order не указан → ставим в конец)"""

        is_insert = order is not None

        if order is None:
            order = await self.photo_repo.count_by_item(item_id)

        new_photo = await self.photo_repo.create(
            item_id=item_id,
            telegram_file_id=telegram_file_id,
            order=order,
        )

        if is_insert:
            # После добавления перестраиваем порядок (без дырок)
            await self.photo_repo.reorder(item_id)

        dto = PhotoOut.model_validate(new_photo)
        logger.info("A photo added for the item: item_id=%s", item_id)
        return dto

    async def add_photos(self, item_id: int, file_ids: list[str]) -> list[PhotoOut]:
        """Добавить несколько фотографий к объявлению.
        Порядок назначается «хвостом» после уже существующих.
        """
        if not file_ids:
            return []

        start_order = await self.photo_repo.count_by_item(item_id)

        result: list[PhotoOut] = []
        for offset, file_id in enumerate(file_ids):
            photo = await self.photo_repo.create(
                item_id=item_id,
                telegram_file_id=file_id,
                order=start_order + offset,
            )
            result.append(PhotoOut.model_validate(photo))

        logger.info("Photos added for the item: item_id=%s count=%s", item_id, len(result))
        return result

    async def delete_photo(self, photo_id: int, *, strict: bool = False) -> bool:
        """Удаляет фото и уплотнить порядок у оставшихся"""

        # ищем фото
        photo = await self.photo_repo.get_by_id(photo_id)
        if not photo:
            if strict:
                raise NotFoundError(f"Фото не найдено: id={photo_id}")
            return False

        # удаляем фото
        deleted = await self.photo_repo.delete(photo_id)
        if not deleted:
            if strict:
                raise NotFoundError(f"Фото не найдено: id={photo_id}")
            return False

        # уплотняем порядок
        await self.photo_repo.reorder(photo.item_id)

        logger.info("The photo id=%s is deleted from the item item_id=%s", photo_id, photo.item_id)
        return True

    # --------------------------------------- Admin-logic --------------------------------------------------
    async def move_photo(self, photo_id: int, direction: Literal["up", "down"], strict: bool = False) -> bool:
        """Перемещает фото вверх или вниз (direction: 'up' | 'down')"""

        photo = await self.photo_repo.get_by_id(photo_id)
        if not photo:
            if strict:
                raise NotFoundError(f"Фото не найдено: id={photo_id}")
            return False

        # repo должен найти соседа и сделать swap атомарно
        ok = await self.photo_repo.swap_with_neighbor(
            item_id=photo.item_id,
            photo_id=photo_id,
            direction=direction
        )
        if not ok and strict:
            raise ConflictError("Нельзя переместить фото (уже крайнее или изменилось)")

        return ok

    async def set_order(self, photo_id: int, new_order: int, strict: bool = False) -> bool:
        """Установить явный order для фото."""
        photo = await self.photo_repo.get_by_id(photo_id)
        if not photo:
            if strict:
                raise NotFoundError(f"Фото не найдено: id={photo_id}")
            return False

        ok = await self.photo_repo.set_order(photo_id=photo_id, item_id=photo.item_id, new_order=new_order)

        if not ok and strict:
            raise ConflictError("Нельзя изменить порядок (позиция вне диапазона или данные изменились)")

        return ok
