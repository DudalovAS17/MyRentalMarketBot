from __future__ import annotations

from typing import Optional

from db.models.admin import AdminAction
from db.repositories.base import BaseRepository

class AdminActionRepository(BaseRepository):
    async def create(
        self,
        *,
        admin_id: int,
        action_type: str,
        entity_type: str,
        entity_id: str,
        note: Optional[str] = None,
        payload: Optional[dict] = None,
    ) -> AdminAction:
        async with self._session() as s:
            obj = AdminAction(
                admin_id=admin_id,
                action_type=action_type,
                entity_type=entity_type,
                entity_id=entity_id,
                note=note,
                payload=payload,
            )
            return await self._add_commit_refresh(s, obj)