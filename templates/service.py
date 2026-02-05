"""Template: Service

Правила:
- Только бизнес-логика
- Принимает простые типы/DTO
- Возвращает Pydantic/DTO
- Работает через репозитории
"""

import logging
from typing import Optional

from repositories.example_repository import ExampleRepository
from schemas.example import ExampleOut

logger = logging.getLogger(__name__)


class ExampleService:
    """Сервис для работы с Example-сущностью."""

    def __init__(self, example_repo: ExampleRepository) -> None:
        self.example_repo = example_repo

    async def get_example_payload(self, user_id: int) -> Optional[ExampleOut]:
        """Бизнес-логика получения данных для пользователя."""
        entity = await self.example_repo.get_by_user_id(user_id)
        if not entity:
            return None
        return ExampleOut.model_validate(entity)

    async def get_example_details(self, example_id: int) -> Optional[ExampleOut]:
        """Бизнес-логика получения деталей сущности."""
        entity = await self.example_repo.get_by_id(example_id)
        return ExampleOut.model_validate(entity) if entity else None