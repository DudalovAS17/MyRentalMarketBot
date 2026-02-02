# services/item_service.py
import logging
from typing import Dict, Any, List, Optional, Union
#from decimal import Decimal
from pydantic import ValidationError
from db.models import Item

#from db.models.item import Item
#from db.models.photo import Photo
from db.repositories.item import ItemRepository
from db.repositories.photo import PhotoRepository
from schemas.item import ItemCreate, ItemUpdate, ItemOut

logger = logging.getLogger(__name__)


class ItemService:
    """Сервис для работы с объявлениями (Items + Photos)."""

    def __init__(self, item_repo: ItemRepository, photo_repo: PhotoRepository) -> None:
        self.item_repo = item_repo
        self.photo_repo = photo_repo

    async def get_all_items(self) -> List[ItemOut]:
        """Вернуть все активные объявления"""
        items = await self.item_repo.get_all()
        return [ItemOut.model_validate(i) for i in items]
        #return [i.to_dict() for i in items]
    """[{"id": 1, "user_id": 123, "title": "Палатка Tramp", ...}, {"id": 2, ...} ] - список"""

    async def get_item_by_id(self, item_id: int) -> Optional[ItemOut]:
        """Вернуть объявление по ID"""
        item = await self.item_repo.get_by_id(item_id)
        return ItemOut.model_validate(item) if item else None
        #return item.to_dict() if item else None
    """{"id": 1, "user_id": 123, "title": "Палатка Tramp",...} - не список, а один объект"""

    async def list_by_user(self, user_id: int) -> List[ItemOut]:
        """Все объявления пользователя"""
        items = await self.item_repo.get_by_user_id(user_id)
        return [ItemOut.model_validate(i) for i in items]
    """[ {"id": 1, "user_id": 123, ...}, {"id": 5,"user_id": 123, ...} ]"""

    async def list_by_category(self, category_id: int) -> List[ItemOut]:
        """Все объявления по категории"""
        items = await self.item_repo.get_by_category(category_id)
        return [ItemOut.model_validate(i) for i in items]
    """[ {"id": 1,.., "category_id": 1,...}, {"id": 2, ..., "category_id": 1,...}]"""

    async def list_by_subcategory(self, subcategory_id: int) -> List[ItemOut]:
        """Все объявления по подкатегории"""
        items = await self.item_repo.get_by_subcategory(subcategory_id)
        return [ItemOut.model_validate(i) for i in items]
    """[{"id": 1, "title": "Палатка Tramp", "subcategory_id": 101,...}]"""

    async def search(self, query: str, *, available_only: bool = True, limit: int = 50, offset: int = 0) \
            -> List[ItemOut]:
        """Поиск объявлений по тексту"""
        items = await self.item_repo.search(query, available_only=available_only, limit=limit, offset=offset)
        return [ItemOut.model_validate(i) for i in items]

    async def create(self, item_data: Union[dict, ItemCreate]) -> Optional[ItemOut]:
        """Создать объявление с фото   (dict (FSM) or ItemCreate (API))"""

        # ✅ Ensure input is a validated Pydantic model
        if isinstance(item_data, dict):
            try:
                item_data = ItemCreate(**item_data)
            except ValidationError as e:
                logger.error(f"Validation error while creating ItemCreate: {e}")
                raise ValueError("Invalid item data structure")

        # 🔧 Persist through repository
        obj: Item = await self.item_repo.create(item_data)
        #obj = await self.item_repo.create(item_data)

        logger.info(f"Создано объявление: id={obj.id}, user_id={obj.user_id}, title={obj.title}")
        #logger.info("Создано объявление: id=%s title=%s", obj.id, obj.title)

        return ItemOut.model_validate(obj) if obj else None


    # ──────────────────────────────────────────── NEW (Admin-Item logic) ────────────────────────────────────────
    async def admin_list_pending(self, page: int) -> tuple[list[ItemOut], bool]:
        """Список объявлений на модерации - PENDING."""
        return await self.admin_list_by_status(status="PENDING", page=page)

    async def admin_list_by_status(self, status: str, page: int) -> tuple[list[ItemOut], bool]:
        """Список объявлений по статусу с пагинацией."""
        page_size = 8
        safe_page = max(page, 1)
        offset = (safe_page - 1) * page_size
        items = await self.item_repo.list_by_status(status=status, limit=page_size + 1, offset=offset)
        has_next = len(items) > page_size
        return [ItemOut.model_validate(i) for i in items[:page_size]], has_next
        # model_validate(i) — превращает ORM объект в Pydantic-объект (ItemOut — Pydantic-схема (DTO))
        # [ItemOut.model_validate(i) for i in items[:page_size]] = “возьми первые 8 Item и преобразуй каждый в ItemOut
        # Почему так делают? Чтобы наружу (в handlers/API) не отдавать ORM, а отдавать чистые данные, согласованные со схемой.
        # items[:page_size] - первые page_size элементов.

    async def admin_set_status(
        self,
        item_id: int,
        new_status: str,
        admin_id: int,
        reason: Optional[str] = None,
    ) -> Optional[ItemOut]:
        """Обновить статус объявления через whitelist переходов."""
        item = await self.item_repo.set_status_with_whitelist(
            item_id=item_id,
            new_status=new_status,
            admin_id=admin_id,
            reason=reason,
        )
        return ItemOut.model_validate(item) if item else None
    # ────────────────────────────────────────────────────────────────────────────────────────────────────────


    async def update(self, item_id: int, update_data: ItemUpdate) -> Optional[ItemOut]:
        """Обновить объявление"""
        obj = await self.item_repo.update(item_id, update_data)
        return ItemOut.model_validate(obj) if obj else None

    async def delete(self, item_id: int) -> bool:
        """Удалить объявление"""
        return bool(await self.item_repo.delete(item_id))


######################## тут норм вроде все, но не 100% ####################################
    
    async def add_item_photo(self, item_id: int | str, telegram_file_id: str, order: int = 0) -> Optional[Dict[str, Any]]:
        """Добавить фото к объявлению. Возвращает словарь фото или None."""

        # безопасно привести id (часто приходит как строка из телеги)
        try:
            item_id = int(item_id)
        except (TypeError, ValueError):
            logger.error("add_item_photo() — неверный item_id: %r", item_id)
            return None

        try:
            photo = await self.photo_repo.create(item_id=item_id, telegram_file_id=telegram_file_id, order=order)
        except Exception as e:
            logger.error("add_item_photo() — ошибка при создании фото для item_id=%s: %s", item_id, e, exc_info=True)
            return None

        if photo:
            logger.info("Добавлено фото id=%s к объявлению id=%s", photo.id, item_id)
            return photo.to_dict() # if hasattr(photo, "to_dict") else photo.__dict__
        logger.error("add_item_photo() — не удалось создать фото для item_id=%s", item_id)
        return None

    async def remove_item_photo(self, photo_id: int | str) -> bool:
        """Удалить фото по id. Возвращает True если удалено, False иначе."""
        try:
            photo_id = int(photo_id)
        except (TypeError, ValueError):
            logger.error("remove_item_photo() — неверный photo_id: %r", photo_id)
            return False

        try:
            res = await self.photo_repo.delete(photo_id)  # возвращает 1/0
        except Exception as e:
            logger.error("remove_item_photo() — ошибка при удалении photo_id=%s: %s", photo_id, e, exc_info=True)
            return False

        if res == 1:
            logger.info("Удалено фото id=%s", photo_id)
            return True

        logger.warning("remove_item_photo() — фото id=%s не найдено", photo_id)
        return False

    async def get_item_photos(self, item_id: int | str) -> List[Dict[str, Any]]:
        """Вернуть список фото (в виде dict) для объявления"""
        try:
            item_id = int(item_id)
        except (TypeError, ValueError):
            logger.error("get_item_photos() — неверный item_id: %r", item_id)
            return []

        photos = await self.photo_repo.get_by_item_id(item_id)
        return [p.to_dict() for p in photos]
        # return [p.to_dict() if hasattr(p, "to_dict") else p.__dict__ for p in photos]
