import logging
from typing import Optional, Literal

from db.repositories.photo import PhotoRepository

from schemas.photo import PhotoOut
from utils.errors import NotFoundError, ConflictError

logger = logging.getLogger(__name__)

class PhotoService:
    """Сервис для управления фотографиями объявления"""

    def __init__(self, photo_repo: PhotoRepository):
        self.photo_repo = photo_repo

    # ────────────────────────────────────────── Read methods ──────────────────────────────────────────────────────────
    async def get_photos_by_item_id(self, item_id: int) -> list[PhotoOut]:
        """Возвращает все фото объявления в правильном порядке."""
        photos = await self.photo_repo.list_by_item_id(item_id)
        return [PhotoOut.model_validate(p) for p in photos]

    async def get_photo_by_id(self, photo_id: int, *, strict: bool = False) -> Optional[PhotoOut]:
        """Получить одно фото"""
        photo = await self.photo_repo.get_by_id(photo_id)
        if not photo:
            if strict:
                raise NotFoundError(f"Фото не найдено: id={photo_id}")
            return None

        return PhotoOut.model_validate(photo)

    # ─────────────────────────────────────────── write methods ────────────────────────────────────────────────────────
    async def create_photo(self, *, item_id: int, telegram_file_id: str, order: Optional[int] = None) -> PhotoOut:
        """Добавляет фото к объявлению

        Если `sort_order` не указан, фото добавляется в конец.
        Если `sort_order` указан, после вставки порядок фотографий уплотняется.
        """

        is_insert = order is not None
        if order is None:
            order = await self.photo_repo.count_by_item(item_id)

        new_photo = await self.photo_repo.create(item_id=item_id, telegram_file_id=telegram_file_id, order=order)
        if not new_photo:
            # Если photo_repo.create() вернул None, то скорее всего item не найден.
            raise NotFoundError(f"Объявление не найдено: id={item_id}")

        if is_insert:
            # После добавления перестраиваем порядок (без дырок)
            await self.photo_repo.reorder(item_id)

        dto = PhotoOut.model_validate(new_photo)
        logger.info("Фото id=%s добавлено к объявлению: item_id=%s", dto.id, item_id)
        return dto

    async def create_photos(self, item_id: int, file_ids: list[str]) -> list[PhotoOut]:
        """Добавить несколько фотографий к объявлению. Порядок назначается «хвостом» после уже существующих"""

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

        logger.info("Фото (count=%s штук) добавлены к объявлению: item_id=%s", len(result), item_id)
        return result

    async def delete_photo(self, photo_id: int, *, strict: bool = False) -> bool:
        """Удаляет фото и уплотнить порядок у оставшихся. True - удалено, False - иначе"""

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

        logger.info("Фото id=%s удалено из объявления item_id=%s", photo_id, photo.item_id)
        return True

    # ──────────────────────────────────────── Order management ────────────────────────────────────────────────────────
    async def move_photo(self, photo_id: int, direction: Literal["up", "down"], strict: bool = False) -> bool:
        """Перемещает фото вверх или вниз (direction: 'up' | 'down') внутри списка фотографий объявления"""

        photo = await self.photo_repo.get_by_id(photo_id)
        if not photo:
            if strict:
                raise NotFoundError(f"Фото не найдено: id={photo_id}")
            return False

        # repo должен найти соседа и сделать swap атомарно
        ok = await self.photo_repo.swap_with_neighbor(item_id=photo.item_id, photo_id=photo_id, direction=direction)
        if not ok and strict:
            raise ConflictError("Нельзя переместить фото (уже крайнее или изменилось)")

        return ok

    async def set_order(self, photo_id: int, new_order: int, strict: bool = False) -> bool:
        """Установить новую позицию (sort_order) фотографии внутри списка фотографий объявления"""
        photo = await self.photo_repo.get_by_id(photo_id)
        if not photo:
            if strict:
                raise NotFoundError(f"Фото не найдено: id={photo_id}")
            return False

        ok = await self.photo_repo.set_order(photo_id=photo_id, item_id=photo.item_id, new_order=new_order)

        if not ok and strict:
            raise ConflictError("Нельзя изменить порядок (позиция вне диапазона или данные изменились)")

        return ok