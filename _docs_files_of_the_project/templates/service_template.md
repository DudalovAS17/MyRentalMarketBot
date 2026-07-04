# Template: Service

Service в этом проекте — бизнес-слой между handlers и repositories.

Правила:
- Принимает простые типы и Pydantic DTO (`ItemCreate`, `ItemUpdate`).
- Работает через repositories / другие services.
- Возвращает DTO (`ItemOut`) или простые значения (`bool`, `tuple`, `list`).
- Не возвращает ORM наружу.
- Не знает про Telegram objects: никаких `Message`, `CallbackQuery`, `FSMContext`, `Router`.
- Бизнес-ошибки выражаем через `utils.errors` (`NotFoundError`, `ConflictError` и т.п.).
- Технические исключения не глотаем: пусть уходят в global error handler.
- Логируем короткие бизнес-события без PII.

---

### Каноничный шаблон

```python
import logging
from typing import Optional

from db.repositories.item import ItemRepository
from schemas.item import ItemCreate, ItemOut, ItemUpdate
from services.rental_service import RentalService
from status.item_status import ItemStatus
from utils.errors import ConflictError, NotFoundError

logger = logging.getLogger(__name__)


class ItemService:
    """Сервис для работы с товарами каталога компании."""

    def __init__(self, item_repo: ItemRepository, rental_service: RentalService) -> None:
        self.item_repo = item_repo
        self.rental_service = rental_service

    # ───────────────────────────────────── DTO helpers ─────────────────────────────────
    @staticmethod
    def _to_out(item) -> ItemOut:
        return ItemOut.model_validate(item)

    @classmethod
    def _to_out_list(cls, items) -> list[ItemOut]:
        return [cls._to_out(item) for item in items]

    # ───────────────────────────────────── reads ───────────────────────────────────────
    async def list_all_items(
        self,
        *,
        available_only: bool = True,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> list[ItemOut]:
        """Вернуть товары каталога; по умолчанию только опубликованные."""
        items = await self.item_repo.list_all(
            active_only=available_only,
            limit=limit,
            offset=offset,
        )
        return self._to_out_list(items)

    async def get_item_by_id(self, item_id: int, *, strict: bool = False) -> Optional[ItemOut]:
        """Вернуть товар по ID."""
        item = await self.item_repo.get_by_id(item_id)
        if not item:
            if strict:
                raise NotFoundError(f"Товар не найден: id={item_id}")
            return None

        return self._to_out(item)

    # ───────────────────────────────────── writes ──────────────────────────────────────
    async def create(
        self,
        item_data: ItemCreate,
        *,
        created_by_admin_id: Optional[int] = None,
        status: ItemStatus = ItemStatus.DRAFT,
    ) -> ItemOut:
        """Создать товар каталога компании."""
        obj = await self.item_repo.create(
            item_data=item_data,
            created_by_admin_id=created_by_admin_id,
            status=status,
        )
        logger.info("Создан товар: id=%s created_by_admin_id=%s", obj.id, created_by_admin_id)
        return self._to_out(obj)

    async def update(
        self,
        item_id: int,
        update_data: ItemUpdate,
        *,
        updated_by_admin_id: Optional[int] = None,
        strict: bool = False,
    ) -> Optional[ItemOut]:
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
```

---

### Checklist
- [ ] Service возвращает DTO, а не ORM.
- [ ] Конвертация ORM → DTO собрана в `_to_out()` / `_to_out_list()`.
- [ ] `strict=True` поднимает бизнес-исключение, `strict=False` возвращает `None` / `False`.
- [ ] Бизнес-конфликты проверяются здесь, а не в repository и не в handler.
- [ ] Нет `Message`, `CallbackQuery`, `FSMContext`, `Router`, keyboard builders.
- [ ] Логи фиксируют бизнес-событие, но не содержат телефоны и лишние персональные данные.