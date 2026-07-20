import logging
from typing import Optional
from dataclasses import dataclass

from db.repositories.item import ItemRepository
from services.rental_service import RentalService

from schemas.item import ItemCreate, ItemUpdate, ItemOut, ItemCharacteristicOut
from utils.errors import ConflictError, NotFoundError
from status.item_status import can_transition, ItemStatus

logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class ItemRentalAvailability:
    can_request: bool
    reason: str
    available_quantity: int | None = None

class ItemService:
    """Сервис для работы с товарами каталога компании."""

    def __init__(self, item_repo: ItemRepository, rental_service: RentalService) -> None:
        self.item_repo = item_repo
        self.rental_service = rental_service

    # ───────────────────────────────────────── DTO helpers ────────────────────────────────────────────────────────────
    @staticmethod
    def _to_out(item) -> ItemOut:
        return ItemOut.model_validate(item)

    @classmethod
    def _to_out_list(cls, items) -> list[ItemOut]:
        return [cls._to_out(item) for item in items]

    # ────────────────────────────────────────── Read methods ──────────────────────────────────────────────────────────
    async def list_all_items(self, *, available_only: bool = True, limit: Optional[int] = None, offset: int = 0) -> list[ItemOut]:
        """Вернуть товары каталога; по умолчанию только опубликованные."""
        items = await self.item_repo.list_all(active_only=available_only, limit=limit, offset=offset)
        return self._to_out_list(items)

    async def get_item_by_id(self, item_id: int, *, strict: bool = False) -> Optional[ItemOut]:
        """Вернуть товар по ID"""
        item = await self.item_repo.get_by_id(item_id)
        if not item:
            if strict:
                raise NotFoundError(f"Товар не найден: id={item_id}")
            return None

        return self._to_out(item)

    async def get_public_item_by_id(self, item_id: int, *, strict: bool = False) -> Optional[ItemOut]:
        """Вернуть товар, который можно показывать клиенту в публичном каталоге."""
        item = await self.item_repo.get_public_by_id(item_id)
        if not item:
            if strict:
                raise NotFoundError(f"Товар не найден или недоступен для каталога: id={item_id}")
            return None

        return self._to_out(item)

    #Убрано list_by_items_user_id - Все товары пользователя

    async def list_items_by_category(self, category_id: int, *, available_only: bool = True) -> list[ItemOut]:
        """Все товары по категории"""
        items = await self.item_repo.list_by_category(category_id, active_only=available_only)
        return self._to_out_list(items)

    async def list_items_by_subcategory(self, subcategory_id: int, *, available_only: bool = True) -> list[ItemOut]:
        """Все товары по подкатегории"""
        items = await self.item_repo.list_by_subcategory(subcategory_id, active_only=available_only)
        return self._to_out_list(items)

    async def list_items_by_created_admin_id(self, admin_id: int, *, available_only: bool = False) -> list[ItemOut]:
        """Вернуть товары каталога, созданные указанным сотрудником компании."""
        items = await self.item_repo.list_by_created_admin_id(admin_id, active_only=available_only)
        return self._to_out_list(items)

    async def list_items_by_updated_admin_id(self, admin_id: int, *, available_only: bool = False) -> list[ItemOut]:
        """Вернуть товары каталога, последний раз обновлённые указанным сотрудником компании."""
        items = await self.item_repo.list_by_updated_admin_id(admin_id, active_only=available_only)
        return self._to_out_list(items)

    async def search_items(self, query: str, *, available_only: bool = True, limit: int = 50, offset: int = 0) -> list[ItemOut]:
        """Искать товары каталога по названию/описанию."""
        if not query.strip():
            return []

        items = await self.item_repo.search(query, active_only=available_only, limit=limit, offset=offset)
        return self._to_out_list(items)

    # ─────────────────────────────────────────── Write methods ────────────────────────────────────────────────────────
    async def create(
            self,
            item_data: ItemCreate,
            *,
            created_by_admin_id: Optional[int] = None,
            status: ItemStatus = ItemStatus.DRAFT
    ) -> ItemOut:
        """Создать товар каталога компании."""
        obj = await self.item_repo.create(
            item_data=item_data,
            created_by_admin_id=created_by_admin_id,
            status=status,
        )
        logger.info("Создан товар: id=%s created_by_admin_id=%s", obj.id, created_by_admin_id)
        return self._to_out(obj)

    async def update(self, item_id: int, update_data: ItemUpdate,
                     *, updated_by_admin_id: Optional[int] = None, strict: bool = False) -> Optional[ItemOut]:
        """Обновить товар каталога."""
        obj = await self.item_repo.update(
            item_id=item_id,
            update_data=update_data,
            updated_by_admin_id=updated_by_admin_id,
        )
        if not obj:
            if strict:
                raise NotFoundError(f"Товар не найден: id={item_id}")
            return None

        dto = self._to_out(obj)
        logger.info("Товар обновлен: id=%s updated_by_admin_id=%s", dto.id, updated_by_admin_id)
        return dto

    async def delete(self, item_id: int, *, strict: bool = False) -> bool:
        """Удалить товар каталога, если по нему нет открытых заявок."""
        has_open = await self.rental_service.has_open_rentals_for_item(item_id)
        if has_open:
            if strict:
                raise ConflictError(f"Нельзя удалить товар id={item_id}: есть открытые заявки аренды")
            return False

        deleted = await self.item_repo.delete(item_id)
        if not deleted:
            if strict:
                raise NotFoundError(f"Товар не найден: id={item_id}")
            return False

        logger.info("Товар удален: id=%s", item_id)
        return True

    # ───────────────────────────────────── Admin-Item logic 🔧 ────────────────────────────────────────────────────────
    async def admin_list_drafts(self, page: int) -> tuple[list[ItemOut], bool]:
        """Вернуть черновики товаров каталога.""" # (на модерации - ранее PENDING)
        return await self.admin_list_by_status(status=ItemStatus.DRAFT, page=page)

    async def admin_list_by_status(self, status: ItemStatus, page: int) -> tuple[list[ItemOut], bool]:
        """Список товаров по статусу с пагинацией"""
        page_size = 8
        safe_page = max(page, 1)
        offset = (safe_page - 1) * page_size

        items = await self.item_repo.list_by_status(status=status, limit=page_size + 1, offset=offset)
        has_next = len(items) > page_size

        return self._to_out_list(items[:page_size]), has_next

    # обдумай зачем нужна нам
    async def admin_set_status(self, item_id: int, new_status: ItemStatus, updated_by_admin_id: Optional[int] = None,
                               *, strict: bool = False) -> Optional[ItemOut]:
        """Смена статуса товара админом с бизнес-проверками"""

        # товар
        item = await self.item_repo.get_by_id(item_id)
        if not item:
            if strict:
                raise NotFoundError(f"Товар для модерации не найдено: id={item_id}")
            return None

        old_status: ItemStatus = item.status
        if old_status == new_status:
            return self._to_out(item)

        # можно ли перейти из старого статуса в новый
        if not can_transition(old_status, new_status):
            if strict:
                raise ConflictError(f"Нельзя сменить статус товара id={item_id}: {old_status.value} -> {new_status.value}")
            return None

        # не опасно ли скрывать/архивировать товар при открытых заявках (???)
        if not await self._ensure_no_open_rentals_for_status(item_id=item_id, new_status=new_status, strict=strict):
            return None

        # Обновляем статус
        updated = await self.item_repo.set_status(item_id=item_id, new_status=new_status, updated_by_admin_id=updated_by_admin_id)
        if not updated:
            if strict:
                raise NotFoundError(f"Товар не найден: id={item_id}")
            return None

        logger.info("Статус товара каталога изменён: id=%s %s->%s admin_id=%s",
                    item_id, old_status.value, new_status.value, updated_by_admin_id)

        return self._to_out(updated)

    # ?
    @staticmethod
    def admin_item_actions_for_status(status: ItemStatus) -> tuple[str, ...]:
        """Вернуть допустимые admin UI-actions для текущего статуса товара."""
        actions: list[str] = []
        if can_transition(status, ItemStatus.ACTIVE):
            actions.append("approve" if status == ItemStatus.DRAFT else "unhide")
        if can_transition(status, ItemStatus.HIDDEN):
            actions.append("hide")
        if can_transition(status, ItemStatus.ARCHIVED):
            actions.append("archive")
        actions.extend(("edit_quantity", "edit_price"))
        return tuple(actions)


    # ─────────────────────────────────────── Business validation ─────────────────────────────────────────────────────
    async def _ensure_no_open_rentals_for_status(self, *, item_id: int, new_status: ItemStatus, strict: bool) -> bool:
        """Не разрешать скрывать/архивировать товар, если по нему есть открытые заявки аренды."""
        if new_status not in {ItemStatus.HIDDEN, ItemStatus.ARCHIVED}:
            return True

        has_open = await self.rental_service.has_open_rentals_for_item(item_id)
        if not has_open:
            return True

        if strict:
            raise ConflictError(f"Нельзя изменить статус товара id={item_id}: есть открытые заявки аренды")
        return False

    # ItemRentalAvailability here
    @staticmethod
    def item_rental_availability(item: ItemOut) -> ItemRentalAvailability: # , *, has_open_rental: bool = False
        """Вернуть доступность товара для аренды и нормализованный код причины."""
        if item.status != ItemStatus.ACTIVE:
            return ItemRentalAvailability(
                can_request=False,
                reason="inactive",
                available_quantity=item.available_quantity,
            )
        if item.available_quantity <= 0:
            return ItemRentalAvailability(
                can_request=False,
                reason="out_of_stock",
                available_quantity=item.available_quantity,
            )
        # if has_open_rental: # пока убираем эту логику - у нас просто кол-во товаров.
        #     return ItemRentalAvailability(
        #         can_request=False,
        #         reason="busy",
        #         available_quantity=item.available_quantity,
        #     )

        return ItemRentalAvailability(
            can_request=True,
            reason="available",
            available_quantity=item.available_quantity,
        )

    # ─────────────────────────────────────────────Item Characteristic──────────────────────────────────────────────────
    async def list_item_characteristics_by_item_id(
        self,
        item_id: int,
        limit: Optional[int] = None,
    ) -> list[ItemCharacteristicOut]:
        """Вернуть характеристики товара в порядке sort_order ASC, id ASC."""
        characteristics = await self.item_repo.list_characteristics_by_item_id(item_id, limit=limit)
        return [ItemCharacteristicOut.model_validate(characteristic) for characteristic in characteristics]