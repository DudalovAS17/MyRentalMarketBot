import enum
import logging
from typing import Optional

from db.repositories.admin import AdminActionRepository
from schemas.admin import AdminActionOut

logger = logging.getLogger(__name__)

class AdminActionService:
    def __init__(self, repo: AdminActionRepository): #  -> None:
        self.repo = repo

    async def log_action(
        self, *,
        admin_id: int,
        action_type: str | enum.Enum,
        entity_type: str | enum.Enum,
        entity_id: str | int,
        note: Optional[str] = None,
        payload: Optional[dict] = None, # Optional[dict[str, Any]]
    ) -> AdminActionOut:
        action_type_str = action_type.value if isinstance(action_type, enum.Enum) else str(action_type)
        entity_type_str = entity_type.value if isinstance(entity_type, enum.Enum) else str(entity_type)

        obj =  await self.repo.create(
            admin_id=admin_id,
            action_type=action_type_str, # привели
            entity_type=entity_type_str, # к
            entity_id=str(entity_id), # строкам
            note=note,
            payload=payload
        )

        return AdminActionOut.model_validate(obj)