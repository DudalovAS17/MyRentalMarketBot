from __future__ import annotations

from typing import Callable, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.admin import AdminAction
from schemas.admin import AdminActionOut


class AdminActionRepository:
    def __init__(self, session_factory: Callable[[], AsyncSession]) -> None:
        self._sf = session_factory

    async def create(
        self,
        *,
        admin_id: int,
        action_type: str,
        entity_type: str,
        entity_id: str,
        note: Optional[str] = None,
        payload: Optional[dict] = None, # Optional[dict[str, Any]]
    ) -> AdminAction:
        async with self._sf() as s:
            obj = AdminAction(
                admin_id=admin_id,
                action_type=action_type,
                entity_type=entity_type,
                entity_id=entity_id,
                note=note,
                payload=payload,
            )
            s.add(obj)
            try:
                await s.commit()
            except Exception:
                await s.rollback()
                raise
            await s.refresh(obj)
            return obj
