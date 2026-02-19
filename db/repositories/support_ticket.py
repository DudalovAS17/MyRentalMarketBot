import logging
from datetime import datetime, timezone
from typing import Callable, List, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.support_ticket import SupportTicket
from schemas.support import SupportTicketCreateInternal
from utils.support_ticket_status import SupportTicketStatus

logger = logging.getLogger(__name__)

class SupportTicketRepository:
    """Репозиторий тикетов поддержки"""
    def __init__(self, session_factory: Callable[[], AsyncSession]):
        self._sf = session_factory

    async def get_by_id(self, ticket_id: int) -> Optional[SupportTicket]:
        """Получить тикет по первичному ключу (id)"""
        async with self._sf() as s:
            return await s.get(SupportTicket, ticket_id)

    async def get_open_by_user_id(self, user_id: int) -> Optional[SupportTicket]:
        """Получить последний открытый тикет пользователя (если существует)"""
        async with self._sf() as s:
            stmt = (
                select(SupportTicket)
                .where(
                    SupportTicket.user_id == user_id,
                    SupportTicket.status == SupportTicketStatus.OPEN,
                )
                #.order_by(desc(SupportTicket.id))
                .order_by(SupportTicket.created_at.desc())
                .limit(1)
            )
            res = await s.execute(stmt)
            return res.scalar_one_or_none() # res.scalars().first()

    async def list_open(self, *, limit: Optional[int] = None, offset: int = 0) -> List[SupportTicket]:
        """Список открытых тикетов (с пагинацией)"""
        async with self._sf() as s:
            stmt = (
                select(SupportTicket)
                .where(SupportTicket.status == SupportTicketStatus.OPEN)
                .order_by(SupportTicket.created_at.desc())
                #.order_by(desc(SupportTicket.id))
                .offset(offset)
                #.limit(limit)
            )
            if limit is not None:
                stmt = stmt.limit(limit)

            res = await s.execute(stmt)
            return list(res.scalars())

    async def close(self, *, ticket_id: int, admin_id: int) -> bool:
        """Техническое закрытие тикета по id. Возвращает True, если запись обновлена"""
        async with self._sf() as s:
            stmt = (
                update(SupportTicket)
                .where(SupportTicket.id == ticket_id)
                .where(SupportTicket.status == SupportTicketStatus.OPEN)
                .values(
                    status=SupportTicketStatus.CLOSED,
                    closed_at=datetime.now(timezone.utc),
                    closed_by_admin_id=admin_id, # telegram id!
                )
            )
            res = await s.execute(stmt)

            try:
                await s.commit()
            except Exception:
                await s.rollback()
                raise

            updated_rows = int(getattr(res, "rowcount", 0) or 0)
            return updated_rows > 0 # похоже на try_update_status в rentals

    async def touch_admin_reply(self, *, ticket_id: int) -> bool:
        """Зачем:
            чтобы сортировать “тикеты, которым давно не отвечали”
            чтобы видеть “последняя активность админа”
            чтобы не плодить лишние таблицы сообщений в MVP
        """
        async with self._sf() as s:
            stmt = (
                update(SupportTicket)
                .where(SupportTicket.id == ticket_id)
                .values(admin_last_reply_at=datetime.now(timezone.utc))
            )
            res = await s.execute(stmt)

            try:
                await s.commit()
            except Exception:
                await s.rollback()
                raise

            updated_rows = int(getattr(res, "rowcount", 0) or 0)
            return updated_rows > 0

    # -------------------------------------------------------------------------------------------------------
    async def create(self, ticket_data: SupportTicketCreateInternal) -> SupportTicket:
        payload = ticket_data.model_dump()
        async with self._sf() as s:
            obj = SupportTicket(**payload)
            s.add(obj)
            try:
                await s.commit()
            except Exception:
                await s.rollback()
                raise

            await s.refresh(obj)
            return obj

    # update() и delete() специально не пишем. Тикет нельзя перезаписать и удалить. Пока так.
