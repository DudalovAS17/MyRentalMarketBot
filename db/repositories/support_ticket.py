import logging
from datetime import datetime, timezone
from typing import Callable, List, Optional

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.support_ticket import SupportTicket
from schemas.support import SupportTicketCreate, SupportTicketUpdate
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
                .limit(limit)
            )
            res = await s.execute(stmt)
            return list(res.scalars())

    async def close(self, *, ticket_id: int, admin_id: int) -> bool:
        """Техническое закрытие тикета по id. Возвращает True, если запись обновлена"""
        async with self._sf() as s:
            ticket = await s.get(SupportTicket, ticket_id)
            if not ticket or ticket.status != SupportTicketStatus.OPEN:
                return False

            ticket.status = SupportTicketStatus.CLOSED
            ticket.closed_at = datetime.now(timezone.utc)
            ticket.closed_by_admin_id = admin_id # это telegram id?

            try:
                await s.commit()
            except Exception:
                await s.rollback()
                raise
            return True


    async def touch_admin_reply(self, *, ticket_id: int) -> None: #bool
        """Зачем:
            чтобы сортировать “тикеты, которым давно не отвечали”
            чтобы видеть “последняя активность админа”
            чтобы не плодить лишние таблицы сообщений в MVP
        """
        async with self._sf() as s:
            ticket = await s.get(SupportTicket, ticket_id)
            if not ticket:
                return None #False

            ticket.admin_last_reply_at = datetime.now(timezone.utc)

            try:
                await s.commit()
            except Exception:
                await s.rollback()
                raise
            return None #True

    # -------------------------------------------------------------------------------------------------------
    # Обдумай оба ниже (собенно про update_data: SupportTicketUpdate -> update_data: dict)

    # ТУТ СЫРО - глаз замылился

    async def create(self, ticket_data: dict) -> SupportTicket:
        async with self._sf() as s:
            #obj = SupportTicket(**ticket_data.model_dump())
            obj = SupportTicket(**ticket_data)
            s.add(obj)
            try:
                await s.commit()
            except Exception as e:
                await s.rollback()
                raise

            await s.refresh(obj)
            return obj

    """
    📌 Сервис теперь сам делает:
        data = ticket_create.model_dump()
        await repo.create(data)
    """

    async def update(self, ticket_id: int, update_data: dict) -> Optional[SupportTicket]:
        async with self._sf() as s:
            obj = await s.get(SupportTicket, ticket_id)
            if not obj:
                return None

            #data = update_data.model_dump(exclude_unset=True)
            #if not data:
            #    return obj

            if not update_data:
                return obj

            #for k, v in data.items():
            for k, v in update_data.items():
                setattr(obj, k, v)

            try:
                await s.commit()
            except Exception:
                await s.rollback()
                raise
            await s.refresh(obj)
            return obj
