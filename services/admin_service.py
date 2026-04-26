import enum
from typing import Optional

from db.repositories.admin import AdminActionRepository

from schemas.admin import AdminActionOut

class AdminActionService:
    """Сервис для записи административных действий в журнал аудита"""

    def __init__(self, repo: AdminActionRepository) -> None:
        self.repo = repo

    async def log_action(
        self, *,
        admin_tg_id: int,
        action_type: str | enum.Enum,
        entity_type: str | enum.Enum,
        entity_id: str | int,
        note: Optional[str] = None,
        payload: dict[str, object] | None = None
    ) -> AdminActionOut:
        """Записать действие администратора и вернуть DTO созданной audit-записи"""

        # приведем к строкам
        action_type_str = action_type.value if isinstance(action_type, enum.Enum) else str(action_type)
        entity_type_str = entity_type.value if isinstance(entity_type, enum.Enum) else str(entity_type)

        obj =  await self.repo.create(
            admin_tg_id=admin_tg_id,
            action_type=action_type_str,
            entity_type=entity_type_str,
            entity_id=str(entity_id),
            note=note,
            payload=payload
        )

        return AdminActionOut.model_validate(obj)