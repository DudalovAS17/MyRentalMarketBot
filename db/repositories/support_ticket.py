from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select, update

from db.models.support_ticket import SupportTicket
from db.repositories.base import BaseRepository
from schemas.support import SupportTicketCreateInternal
from status.support_ticket_status import SupportTicketStatus


class SupportTicketRepository(BaseRepository):
    """Репозиторий тикетов поддержки"""
    # ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    async def get_by_id(self, ticket_id: int) -> Optional[SupportTicket]:
        """Получить тикет по первичному ключу (id)"""
        async with self._session() as s:
            return await s.get(SupportTicket, ticket_id)

    async def get_open_by_user_id(self, user_id: int) -> Optional[SupportTicket]:
        """Получить последний открытый тикет пользователя (если существует)"""
        async with self._session() as s:
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
            return await self._one_or_none(s, stmt)

    async def list_open(self, *, limit: Optional[int] = None, offset: int = 0) -> list[SupportTicket]:
        """Список открытых тикетов (с пагинацией)"""
        async with self._session() as s:
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

            return await self._list(s, stmt)

    async def close(self, *, ticket_id: int, admin_id: int) -> bool:
        """Техническое закрытие тикета по id. Возвращает True, если запись обновлена"""
        async with self._session() as s:
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
            return await self._execute_update_commit(s, stmt) # похоже на try_update_status в rentals

    async def touch_admin_reply(self, *, ticket_id: int) -> bool:
        """Зачем:
            чтобы сортировать “тикеты, которым давно не отвечали”
            чтобы видеть “последняя активность админа”
            чтобы не плодить лишние таблицы сообщений в MVP
        """
        async with self._session() as s:
            stmt = (
                update(SupportTicket)
                .where(SupportTicket.id == ticket_id)
                .values(admin_last_reply_at=datetime.now(timezone.utc))
            )
            return await self._execute_update_commit(s, stmt)

    # ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    async def create(self, ticket_data: SupportTicketCreateInternal) -> SupportTicket:
        payload = ticket_data.model_dump()
        async with self._session() as s:
            obj = SupportTicket(**payload)
            return await self._add_commit_refresh(s, obj)

    # update() и delete() специально не пишем. Тикет нельзя перезаписать и удалить. Пока так.