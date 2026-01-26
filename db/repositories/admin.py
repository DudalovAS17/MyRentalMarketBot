import logging
from typing import Callable, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.admin import AdminAction

logger = logging.getLogger(__name__)

class AdminActionRepository:
    def __init__(self, session_factory: Callable[[], AsyncSession]) -> None:
        self._sf = session_factory

    async def create(
        self,
        admin_id: int,
        action_type: str,
        entity_type: str,
        entity_id: int,
        payload: Optional[dict] = None, # str
    ) -> AdminAction:
        async with self._sf() as s:
            obj = AdminAction(
                admin_id=admin_id,
                action_type=action_type,
                entity_type=entity_type,
                entity_id=entity_id,
                payload=payload,
            )
            s.add(obj)
            #try:
            await s.commit()
            await s.refresh(obj)
            return obj
            #except Exception as e:
            #    await s.rollback()
            #    logger.exception("Не удалось сохранить audit log для entity=%s id=%s", entity_type, entity_id)
            #    raise
