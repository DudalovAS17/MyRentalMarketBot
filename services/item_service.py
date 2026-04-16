import logging
from typing import Optional

from db.repositories.item import ItemRepository
from db.repositories.photo import PhotoRepository
#from db.repositories.rental import RentalRepository
from services.rental_service import RentalService

from schemas.item import ItemCreate, ItemUpdate, ItemOut
from schemas.photo import PhotoOut
from utils.errors import ConflictError, NotFoundError
from status.item_status import can_transition, ItemStatus

logger = logging.getLogger(__name__)

class ItemService:
    """Сервис для работы с объявлениями (Items + Photos)."""

    def __init__(
            self,
            item_repo: ItemRepository,
            photo_repo: PhotoRepository,
            #rental_repo: RentalRepository # тут только кросс-доменный инвариант в moderate_set_status() - оставляем
            rental_service: RentalService, # ItemService больше не знает про RentalRepository
    ) -> None:
        self.item_repo = item_repo
        self.photo_repo = photo_repo
        #self.rental_repo = rental_repo
        self.rental_service = rental_service

    async def list_all_items(
        self,
        *,
        available_only: bool = True,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> list[ItemOut]:
        """Список объявлений (по умолчанию только доступные)"""
        items = await self.item_repo.list_all(active_only=available_only, limit=limit, offset=offset)
        return [ItemOut.model_validate(i) for i in items]

    async def get_item_by_id(self, item_id: int, *, strict: bool = False) -> Optional[ItemOut]:
        """Вернуть объявление по ID"""
        item = await self.item_repo.get_by_id(item_id)
        if not item:
            if strict:
                raise NotFoundError(f"Объявление не найдено: id={item_id}")
            return None
        return ItemOut.model_validate(item)

    async def list_by_user(self, user_id: int, *, available_only: bool = False) -> list[ItemOut]:
        """Все объявления пользователя"""
        items = await self.item_repo.list_by_user_id(user_id, active_only=available_only)
        return [ItemOut.model_validate(i) for i in items]

    async def list_by_category(self, category_id: int, *, available_only: bool = True) -> list[ItemOut]:
        """Все объявления по категории"""
        items = await self.item_repo.list_by_category(category_id, active_only=available_only)
        return [ItemOut.model_validate(i) for i in items]

    async def list_by_subcategory(self, subcategory_id: int, *, available_only: bool = True) -> list[ItemOut]:
        """Все объявления по подкатегории"""
        items = await self.item_repo.list_by_subcategory(subcategory_id, active_only=available_only)
        return [ItemOut.model_validate(i) for i in items]

    async def search(
            self,
            query: str,
            *,
            available_only: bool = True,
            limit: int = 50,
            offset: int = 0
    ) -> list[ItemOut]:
        """Поиск объявлений по названию/описанию"""
        items = await self.item_repo.search(query, active_only=available_only, limit=limit, offset=offset)
        return [ItemOut.model_validate(i) for i in items]

    # ───────────────────────────────────── NEW (Admin-Item logic) 🔧 ────────────────────────────────────────
    async def admin_list_pending(self, page: int) -> tuple[list[ItemOut], bool]:
        """Список объявлений на модерации - PENDING."""
        return await self.admin_list_by_status(status=ItemStatus.PENDING, page=page)

    async def admin_list_by_status(self, status: ItemStatus, page: int) -> tuple[list[ItemOut], bool]:
        """Список объявлений по статусу с пагинацией."""
        page_size = 8
        safe_page = max(page, 1)
        offset = (safe_page - 1) * page_size

        items = await self.item_repo.list_by_status(status=status, limit=page_size + 1, offset=offset)
        has_next = len(items) > page_size

        return [ItemOut.model_validate(i) for i in items[:page_size]], has_next

    async def moderate_set_status( # admin_set_status
            self,
            item_id: int,
            new_status: ItemStatus,
            admin_id: int,
            reason: Optional[str] = None,
            strict: bool = False
    ) -> Optional[ItemOut]:
        """Смена статуса объявления админом (?) с бизнес-проверками (whitelist + открытые сделки)."""
        item = await self.item_repo.get_by_id(item_id)
        if not item:
            if strict:
                raise NotFoundError(f"Объявление для модерации не найдено: id={item_id}")
            return None

        # Проверка whitelist переходов (бизнес-правило)
        old_status: ItemStatus = item.status
        if not can_transition(old_status, new_status):
            if strict:
                raise ConflictError(  # old_status,  new_status
                    f"Нельзя сменить статус объявления id={item_id}: "
                    f"{old_status.value} -> {new_status.value}")
            return None

        # Есть открытые сделки - нельзя скрыть объявление!
        # ТОЛЬКО при скрытии объявления возникает риск сломать активную сделку, поэтому
        if new_status == ItemStatus.HIDDEN:  # (отклонено админом)
            #has_open = await self.rental_repo.has_open_rentals_for_item(item_id)
            has_open = await self.rental_service.has_open_rentals_for_item(item_id)
            if has_open:
                if strict:
                    raise ConflictError(f"Нельзя скрыть объявление id={item_id}: есть открытые сделки")
                return None

        # Обновляем статус
        updated = await self.item_repo.set_status(item_id=item_id, new_status=new_status, admin_user_id=admin_id,
                                                  reason=reason)

        if not updated:  # теоретически item мог исчезнуть между get_by_id и set_status
            if strict:
                raise NotFoundError(f"Объявление не найдено: id={item_id}")
            return None

        logger.info(
            "Item moderated: id=%s %s->%s admin_id=%s",
            item_id, old_status.value, new_status.value, admin_id
        )

        return ItemOut.model_validate(updated)

    # ────────────────────────────────────────────────────────────────────────────────────────────────────────
    async def create(self, user_id: int, item_data: ItemCreate) -> ItemOut:
        """Создать объявление с фото"""
        obj = await self.item_repo.create(user_id=user_id, item_data=item_data)
        logger.info("Создано объявление: id=%s user_id=%s", obj.id, user_id)
        return ItemOut.model_validate(obj)

    async def update(self, item_id: int, update_data: ItemUpdate, *, strict: bool = False) -> Optional[ItemOut]:
        """Обновить объявление"""
        obj = await self.item_repo.update(item_id, update_data)
        if not obj:
            if strict:
                raise NotFoundError(f"Объявление не найдено: id={item_id}")
            return None

        dto = ItemOut.model_validate(obj)
        logger.info("Item updated id=%s", dto.id)
        return dto

    async def delete(self, item_id: int, *, strict: bool = False) -> bool:
        """Удалить объявление"""
        deleted = await self.item_repo.delete(item_id)
        if not deleted:
            if strict:
                raise NotFoundError(f"Объявление не найдено: id={item_id}")
            return False

        logger.info("Item deleted id=%s", item_id)
        return True

    # ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    async def add_item_photo(self, item_id: int, telegram_file_id: str, *, order: int = 0) -> PhotoOut:
        """Добавить фото к объявлению"""
        photo = await self.photo_repo.create(item_id=item_id, telegram_file_id=telegram_file_id, order=order)
        if not photo:
            # Если photo_repo.create() вернул None, то скорее всего item не найден.
            raise NotFoundError(f"Объявление не найдено: id={item_id}")

        dto = PhotoOut.model_validate(photo)
        logger.info("Photo added: id=%s item_id=%s", dto.id, item_id)
        return dto

    async def remove_item_photo(self, photo_id: int, *, strict: bool = False) -> bool:
        """Удалить фото по id. Возвращает True если удалено, False иначе."""
        deleted = await self.photo_repo.delete(photo_id)
        if not deleted:
            if strict:
                raise NotFoundError(f"Фото не найдено: id={photo_id}")
            return False

        logger.info("Photo deleted id=%s", photo_id)
        return True

    async def get_item_photos(self, item_id: int) -> list[PhotoOut]:
        """Вернуть список фото для объявления"""
        photos = await self.photo_repo.list_by_item_id(item_id)
        return [PhotoOut.model_validate(p) for p in photos]