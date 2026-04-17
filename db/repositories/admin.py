from db.models.admin import AdminAction
from db.repositories.base import BaseRepository


class AdminActionRepository(BaseRepository):
    """Репозиторий журнала действий администратора"""

    async def create(
        self,
        *,
        admin_tg_id: int,
        action_type: str,
        entity_type: str,
        entity_id: str,
        note: str | None = None,
        payload: dict[str, object] | None = None,
    ) -> AdminAction:
        """Создать запись о действии администратора"""
        async with self._session() as s:
            obj = AdminAction(
                admin_tg_id=admin_tg_id,
                action_type=action_type,
                entity_type=entity_type,
                entity_id=entity_id,
                note=note,
                payload=payload,
            )
            return await self._add_commit_refresh(s, obj)