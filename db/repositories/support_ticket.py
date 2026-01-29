import logging
from datetime import datetime, timezone
from typing import Callable, List, Optional

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.support_ticket import SupportTicket, SupportTicketStatus
from schemas.support import SupportTicketCreate, SupportTicketUpdate

logger = logging.getLogger(__name__)

class SupportTicketRepository:
    """Репозиторий тикетов поддержки"""
    def __init__(self, session_factory: Callable[[], AsyncSession]):
        self._sf = session_factory

    async def create(self, ticket_data: SupportTicketCreate) -> SupportTicket:
        async with self._sf() as s:
            obj = SupportTicket(**ticket_data.model_dump())
            s.add(obj)
            try:
                await s.commit()
                await s.refresh(obj)
                logger.info("create() — тикет успешно создан, id=%s", obj.id)
                return obj
            except Exception as e:
                await s.rollback()
                logger.error("create() — ошибка при создании тикета: %s", e, exc_info=True)
                raise

    """
    # не смотрел
    async def update(self, ticket_id: int, update_data: SupportTicketUpdate) -> int:
        async with self._sf() as s:
            obj = await s.get(SupportTicket, ticket_id)
            if not obj:
                logger.warning("update() — тикет id=%s не найден", ticket_id)
                return 0

            data = update_data.model_dump(exclude_unset=True)
            if not data:
                logger.info("update() — изменений для тикета id=%s нет", ticket_id)
                return 0

            for k, v in data.items():
                setattr(obj, k, v)

            try:
                await s.commit()
                await s.refresh(obj)
                logger.info("update() — тикет id=%s успешно обновлён", ticket_id)
                return 1
            except Exception as e:
                await s.rollback()
                logger.error("update() — ошибка при обновлении тикета id=%s: %s", ticket_id, e, exc_info=True)
                raise
    """

    async def get_by_id(self, ticket_id: int) -> Optional[SupportTicket]:
        async with self._sf() as s:
            #stmt = select(SupportTicket).where(SupportTicket.id == ticket_id)
            #res = await s.execute(stmt)
            #return res.scalar_one_or_none()
            return await s.get(SupportTicket, ticket_id)

    async def get_open_by_user_id(self, user_id: int) -> Optional[SupportTicket]:
        async with self._sf() as s:
            stmt = (
                select(SupportTicket)
                .where(
                    SupportTicket.user_id == user_id,
                    SupportTicket.status == SupportTicketStatus.OPEN,
                )
                #.order_by(desc(SupportTicket.id))
                .order_by(SupportTicket.created_at.desc())
                #.limit(1)
            )
            res = await s.execute(stmt)
            return res.scalars().first() # res.scalar_one_or_none()

    async def list_open(self, *, limit: int, offset: int) -> List[SupportTicket]:
        async with self._sf() as s:
            stmt = (
                select(SupportTicket)
                .where(SupportTicket.status == SupportTicketStatus.OPEN)
                .order_by(SupportTicket.created_at.desc())
                #.order_by(desc(SupportTicket.id))
                .offset(offset)
                .limit(limit)
            )
            res = await s.execute(stmt)
            return list(res.scalars().all())

    async def close(self, *, ticket_id: int, admin_id: int) -> bool:
        async with self._sf() as s:
            ticket = await s.get(SupportTicket, ticket_id)
            if not ticket or ticket.status != SupportTicketStatus.OPEN:
                return False

            ticket.status = SupportTicketStatus.CLOSED
            ticket.closed_at = datetime.now(timezone.utc)
            ticket.closed_by_admin_id = admin_id

            try:
                await s.commit()
                return True
            except Exception:
                await s.rollback()
                raise


    async def touch_admin_reply(self, *, ticket_id: int) -> None:
        """Зачем:
            чтобы сортировать “тикеты, которым давно не отвечали”
            чтобы видеть “последняя активность админа”
            чтобы не плодить лишние таблицы сообщений в MVP
        """
        async with self._sf() as s:
            ticket = await s.get(SupportTicket, ticket_id)
            if not ticket:
                return

            ticket.admin_last_reply_at = datetime.now(timezone.utc)

            try:
                await s.commit()
            except Exception:
                await s.rollback()
                raise