import logging
from typing import Optional

from db.repositories.item import ItemRepository
from services.rental_service import RentalService

from schemas.item import ItemCreate, ItemUpdate, ItemOut
from utils.errors import ConflictError, NotFoundError
from status.item_status import can_transition, ItemStatus

logger = logging.getLogger(__name__)

class ItemService:
    """Сервис для работы с объявлениями"""

    def __init__(self, item_repo: ItemRepository, rental_service: RentalService) -> None:
        self.item_repo = item_repo
        self.rental_service = rental_service

    # ────────────────────────────────────────── Read methods ──────────────────────────────────────────────────────────
    async def list_all_items(self, *, available_only: bool = True, limit: Optional[int] = None, offset: int = 0) -> list[ItemOut]:
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

    async def list_by_items_user_id(self, user_id: int, *, available_only: bool = False) -> list[ItemOut]:
        """Все объявления пользователя"""
        items = await self.item_repo.list_by_user_id(user_id, active_only=available_only)
        return [ItemOut.model_validate(i) for i in items]

    async def list_items_by_category(self, category_id: int, *, available_only: bool = True) -> list[ItemOut]:
        """Все объявления по категории"""
        items = await self.item_repo.list_by_category(category_id, active_only=available_only)
        return [ItemOut.model_validate(i) for i in items]

    async def list_items_by_subcategory(self, subcategory_id: int, *, available_only: bool = True) -> list[ItemOut]:
        """Все объявления по подкатегории"""
        items = await self.item_repo.list_by_subcategory(subcategory_id, active_only=available_only)
        return [ItemOut.model_validate(i) for i in items]

    async def search_items(self, query: str, *, available_only: bool = True, limit: int = 50, offset: int = 0) -> list[ItemOut]:
        """Поиск объявлений по названию/описанию"""
        items = await self.item_repo.search(query, active_only=available_only, limit=limit, offset=offset)
        return [ItemOut.model_validate(i) for i in items]

    # ─────────────────────────────────────────── write methods ────────────────────────────────────────────────────────
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
        logger.info("Объявление обновлено: id=%s", dto.id)
        return dto

    async def delete(self, item_id: int, *, strict: bool = False) -> bool:
        """Удалить объявление"""
        deleted = await self.item_repo.delete(item_id)
        if not deleted:
            if strict:
                raise NotFoundError(f"Объявление не найдено: id={item_id}")
            return False

        logger.info("Объявление удалено: id=%s", item_id)
        return True

    # ───────────────────────────────────── Admin-Item logic 🔧 ────────────────────────────────────────────────────────
    async def admin_list_pending(self, page: int) -> tuple[list[ItemOut], bool]:
        """Список объявлений на модерации - PENDING"""
        return await self.admin_list_by_status(status=ItemStatus.PENDING, page=page)

    async def admin_list_by_status(self, status: ItemStatus, page: int) -> tuple[list[ItemOut], bool]:
        """Список объявлений по статусу с пагинацией"""
        page_size = 8
        safe_page = max(page, 1)
        offset = (safe_page - 1) * page_size

        items = await self.item_repo.list_by_status(status=status, limit=page_size + 1, offset=offset)
        has_next = len(items) > page_size

        return [ItemOut.model_validate(i) for i in items[:page_size]], has_next

    async def admin_set_status(self, item_id: int, new_status: ItemStatus, admin_user_id: int, reason: Optional[str] = None,
                                  strict: bool = False) -> Optional[ItemOut]:
        """Смена статуса объявления админом с бизнес-проверками (whitelist + открытые сделки)"""
        item = await self.item_repo.get_by_id(item_id)
        if not item:
            if strict:
                raise NotFoundError(f"Объявление для модерации не найдено: id={item_id}")
            return None

        # Проверка whitelist переходов (бизнес-правило)
        old_status: ItemStatus = item.status
        if not can_transition(old_status, new_status):
            if strict:
                raise ConflictError(
                    f"Нельзя сменить статус объявления id={item_id}: {old_status.value} -> {new_status.value}"
                )
            return None

        # ТОЛЬКО при скрытии объявления возникает риск сломать активную сделку, поэтому
        if new_status == ItemStatus.HIDDEN:
            has_open = await self.rental_service.has_open_rentals_for_item(item_id)
            if has_open:
                if strict:
                    raise ConflictError(f"Нельзя скрыть объявление id={item_id}: есть открытые сделки")
                return None

        # Обновляем статус
        updated = await self.item_repo.set_status(item_id=item_id, new_status=new_status, admin_user_id=admin_user_id,
                                                  reason=reason)

        if not updated:
            if strict:
                raise NotFoundError(f"Объявление не найдено: id={item_id}")
            return None

        logger.info(
            "Объявление прошло модерацию: id=%s %s->%s admin_id=%s",
            item_id, old_status.value, new_status.value, admin_user_id
        )

        return ItemOut.model_validate(updated)