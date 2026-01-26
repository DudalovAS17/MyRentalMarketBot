#import json
#import logging
from typing import Optional #, Any, Mapping
from db.repositories.admin import AdminActionRepository

# logger = logging.getLogger(__name__)

class AdminActionService:
    def __init__(self, repo: AdminActionRepository): #  -> None:
        self.repo = repo

    async def log_action(
        self, # *,
        admin_id: int,
        action_type: str,
        entity_type: str,
        entity_id: int,
        payload: Optional[dict] = None, # Mapping[str, Any]
    ): #  -> None:
        # try:
        return await self.repo.create(
            admin_id=admin_id,
            action_type=action_type,
            entity_type=entity_type,
            entity_id=entity_id,
            payload=payload, # = json.dumps(payload, ensure_ascii=False),
        )
        # except Exception:
        # logger.exception(
        #     "Audit log failed: admin_id=%s action=%s entity=%s id=%s",
        #     admin_id,
        #     action_type,
        #     entity_type,
        #     entity_id,
        # )
        # raise