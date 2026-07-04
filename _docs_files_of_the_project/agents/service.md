# AGENT: Services

Файл задаёт правила для слоя `services/` в `MyRentalMarketBot`.

Нужен агентам, которые:
- анализируют business-layer;
- добавляют service-классы и методы;
- ревьюят границы `handler ↔ service`, `service ↔ repository`, `service ↔ schema`, `service ↔ status`.

Главный принцип:

> Service знает, **что допустимо по правилам продукта**, но не знает, **как это показать в Telegram** и **как писать SQL**.

---

## 1) Scope слоя

`services/` — business/orchestration layer.

Разрешено:
- primitive args (`int`, `str`, `bool`, `Decimal`, `datetime`);
- Pydantic DTO (`Create`, `Update`, `Out`, internal/draft если нужно);
- вызовы repositories и других services;
- business checks, conflicts, ownership/role/participant policy;
- статусные переходы через функции/enum из `status/*`;
- mapping ORM → DTO через `model_validate()`;
- короткие business logs без PII;
- domain exceptions из `utils.errors` / `utils.domain_exceptions`.

Запрещено:
- `Message`, `CallbackQuery`, `FSMContext`;
- клавиатуры, callback data, user-facing тексты;
- SQLAlchemy `select/update/delete/session/commit/refresh`;
- возврат ORM наружу;
- форматирование UI-ответов.

---

## 2) Контракты

Public service method принимает:
- DTO + actor ids для write-операций;
- primitive ids + flags для read-операций;
- `strict: bool = False`, если метод может “не найти” сущность;
- enum-статусы проекта (`ItemStatus`, `RentalStatus`, `SupportTicketStatus`, ...), если это часть домена.

Public service method возвращает:
- `XxxOut`;
- `Optional[XxxOut]`;
- `list[XxxOut]`;
- `bool` / `int` для command-like операций;
- `tuple[list[XxxOut], bool]` для пагинации (`items, has_next`).

Public service method не возвращает:
- ORM;
- SQLAlchemy objects;
- Telegram objects;
- текст/клавиатуру для пользователя.

---

## 3) Каноничный service pattern

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

    @staticmethod
    def _to_out(item) -> ItemOut:
        return ItemOut.model_validate(item)

    @classmethod
    def _to_out_list(cls, items) -> list[ItemOut]:
        return [cls._to_out(item) for item in items]

    async def get_item_by_id(self, item_id: int, *, strict: bool = False) -> Optional[ItemOut]:
        item = await self.item_repo.get_by_id(item_id)
        if not item:
            if strict:
                raise NotFoundError(f"Товар не найден: id={item_id}")
            return None
        return self._to_out(item)

    async def create(
        self,
        item_data: ItemCreate,
        *,
        created_by_admin_id: Optional[int] = None,
        status: ItemStatus = ItemStatus.DRAFT,
    ) -> ItemOut:
        obj = await self.item_repo.create(
            item_data=item_data,
            created_by_admin_id=created_by_admin_id,
            status=status,
        )
        logger.info("Создан товар: id=%s created_by_admin_id=%s", obj.id, created_by_admin_id)
        return self._to_out(obj)

    async def delete(self, item_id: int, *, strict: bool = False) -> bool:
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

## 4) `strict` contract

Канон:
- `strict=False` → `None` / `False` для нормальной UX-ветки;
- `strict=True` → business exception (`NotFoundError`, `ConflictError`, domain error).

Handler решает, какой UX показать пользователю.
Service решает, какая business-ситуация произошла.

---

## 5) Status и policy

Статусы живут в `status/*`:
- `ItemStatus` и `can_transition`;
- `RentalStatus`;
- `SupportTicketStatus`;
- `AccountStatus`;
- админские статусы/состояния, если это доменный контракт.

Service обязан:
- проверять допустимость перехода;
- не доверять handler-у как источнику policy;
- держать ownership/role/participant checks здесь, если это бизнес-правило.

---

## 6) Checklist

- [ ] Нет Telegram/FSM/UI imports.
- [ ] Нет SQLAlchemy imports.
- [ ] Repo возвращает ORM, service маппит в DTO.
- [ ] Public method не возвращает ORM.
- [ ] Business conflicts живут здесь, не в handler и не в repository.
- [ ] `strict` поведение единообразно.
- [ ] Логи короткие и без телефонов/PII.
- [ ] Actor IDs явно названы (`created_by_admin_id`, `updated_by_admin_id`, `user_id`, `telegram_id`).