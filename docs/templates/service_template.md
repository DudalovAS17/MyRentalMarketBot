**Template: Service**

*Правила:*
- Только бизнес-логика
- Принимает простые типы/DTO
- Возвращает Pydantic/DTO
- Работает через репозитории
- No Telegram/FSM objects


```
import logging
from typing import Optional

from repositories.example_repository import ExampleRepository
from schemas.example import ExampleCreate, ExampleOut, ExampleUpdate
from utils.errors import NotFoundError

logger = logging.getLogger(__name__)


class ExampleService:
    """Сервис для работы с Example-сущностью (бизнес-слой)."""

    def __init__(self, example_repo: ExampleRepository) -> None:
        self.example_repo = example_repo

    # ──────────────────────────────────────────────────────────────────────────────────────────────────

    async def get_by_id(self, example_id: int, *, strict: bool = False) -> Optional[ExampleOut]:
        """
        Получить сущность по ID.

        - strict=False: вернуть None, если не найдено.
        - strict=True: если не найдено -> ValueError (ошибка бизнес-сценария).
        """
        entity = await self.example_repo.get_by_id(example_id)
        if not entity:
            if strict:
                raise ValueError(f"Сущность Example не найдена: id={example_id}") # NotFoundError
            return None
        return ExampleOut.model_validate(entity)

    async def get_by_telegram_id(self, telegram_user_id: int, *, strict: bool = False) -> Optional[ExampleOut]:
        """
        Получить сущность по Telegram ID.

        - strict=False: вернуть None, если не найдено.
        - strict=True: если не найдено -> ValueError (ошибка бизнес-сценария).
        """
        entity = await self.example_repo.get_by_telegram_id(telegram_user_id)
        if not entity:
            if strict:
                raise ValueError(f"Сущность Example не найдена по Telegram ID: {telegram_user_id}")
            return None
        return ExampleOut.model_validate(entity)

    # ─────────────────────────────────────────────────────────────────────────────────────────────────

    async def create(self, payload: ExampleCreate, *, actor_db_user_id: Optional[int] = None) -> ExampleOut:
        """
        Создать сущность. Возвращает DTO созданного объекта.
        Технические ошибки не подавляются (исключение пробрасывается выше).

        Логи (бизнес-событие):
        - фиксируем факт создания и того, кто инициировал (если есть).
        """
        obj = await self.example_repo.create(payload)
        dto = ExampleOut.model_validate(obj)

        # Бизнес-событие (коротко, без stacktrace)
        if actor_db_user_id is not None:
            logger.info("Example создан id=%s actor_db_user_id=%s", dto.id, actor_db_user_id)
        else:
            logger.info("Example создан id=%s", dto.id)

        return dto


    async def update(
            self,
            example_id: int,
            payload: ExampleUpdate,
            *,
            actor_db_user_id: Optional[int] = None,
            strict: bool = False,
    ) -> Optional[ExampleOut]:
        """
        Обновить сущность (частичное обновление).

        - strict=False: возвращает None, если сущность не найдена.
        - strict=True: кидает ValueError, если сущность не найдена.

        Технические ошибки не подавляются.

        Логи (бизнес-событие):
        - фиксируем факт обновления, только если объект реально найден/обновлён.
        """
        obj = await self.example_repo.update(example_id, payload)
        if not obj:
            if strict:
                raise ValueError(f"Нельзя обновить: Example не найден id={example_id}") # NotFoundError
            return None

        dto = ExampleOut.model_validate(obj)

        if actor_db_user_id is not None:
            logger.info("Example обновлён: id=%s actor_db_user_id=%s", dto.id, actor_db_user_id)
        else:
            logger.info("Example обновлён: id=%s", dto.id)

        return dto

    async def delete(
            self,
            example_id: int,
            *,
            actor_db_user_id: Optional[int] = None,
            strict: bool = False,
    ) -> bool:
        """
        Удалить сущность.

        - strict=False: возвращает False, если не найдено.
        - strict=True: кидает ValueError, если не найдено.

        Технические ошибки не подавляются.

        Логи (бизнес-событие):
        - фиксируем удаление только если реально удалено.
        """
        deleted = await self.example_repo.delete(example_id)
        if not deleted:
            if strict:
                raise ValueError(f"Нельзя удалить: Example не найден id={example_id}") # NotFoundError
            return False

        if actor_db_user_id is not None:
            logger.info("Example удалён: id=%s actor_db_user_id=%s", example_id, actor_db_user_id)
        else:
            logger.info("Example удалён: id=%s", example_id)

        return True
```