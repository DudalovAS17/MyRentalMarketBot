from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import func, select, update

from db.models.support_ticket import SupportTicket
from db.repositories.base import BaseRepository

from schemas.support import SupportTicketCreateInternal, SupportTicketAdminUpdate
from status.support_ticket_status import SupportTicketStatus


class SupportTicketRepository(BaseRepository):
    """Репозиторий обращений клиентов в поддержку."""

    # ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    @staticmethod
    def _apply_recent_order(stmt):
        """Стабильный порядок выдачи обращений: новые сначала."""
        return stmt.order_by(SupportTicket.created_at.desc(), SupportTicket.id.desc())

    @staticmethod
    def _apply_pagination(stmt, *, limit: Optional[int], offset: int):
        if limit is not None:
            stmt = stmt.limit(limit).offset(offset)
        return stmt

    @staticmethod
    def _apply_id_filter(stmt, ticket_id: int):
        """Оставить только обращение с указанным ID."""
        return stmt.where(SupportTicket.id == ticket_id)

    @staticmethod
    def _apply_status_filter(stmt, status: SupportTicketStatus):
        """Оставить только обращения с указанным статусом."""
        return stmt.where(SupportTicket.status == status)

    @staticmethod
    def _apply_user_filter(stmt, user_id: int):
        """Оставить только обращения клиента."""
        return stmt.where(SupportTicket.user_id == user_id)

    @staticmethod
    def _apply_item_filter(stmt, item_id: int):
        """Оставить только обращения по товару."""
        return stmt.where(SupportTicket.item_id == item_id)

    @staticmethod
    def _apply_rental_filter(stmt, rental_id: int):
        """Оставить только обращения по заявке на аренду."""
        return stmt.where(SupportTicket.rental_id == rental_id)

    @staticmethod
    def _apply_closed_by_admin_filter(stmt, admin_id: int):
        """Оставить только обращения, закрытые указанным администратором/менеджером."""
        return stmt.where(SupportTicket.closed_by_admin_id == admin_id)

    @staticmethod
    def _apply_ticket_kind_filter(stmt, kind: str):
        """Оставить обращения нужного клиентского контура."""
        if kind == "items":
            return stmt.where(SupportTicket.item_id.is_not(None), SupportTicket.rental_id.is_(None))
        if kind == "rentals":
            return stmt.where(SupportTicket.rental_id.is_not(None))
        if kind == "general":
            return stmt.where(SupportTicket.item_id.is_(None), SupportTicket.rental_id.is_(None))
        return stmt

    # ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    async def get_by_id(self, ticket_id: int) -> Optional[SupportTicket]:
        """Получить обращение по ID."""
        async with self._session() as s:
            return await s.get(SupportTicket, ticket_id)

    async def get_open_by_user_id(self, user_id: int, *, kind: str | None = None, offset: int = 0) -> Optional[SupportTicket]:
        """Получить последнее открытое обращение клиента, если оно существует."""
        async with self._session() as s:
            stmt = select(SupportTicket)
            stmt = self._apply_user_filter(stmt, user_id)
            stmt = self._apply_status_filter(stmt, SupportTicketStatus.OPEN)

            if kind:
                stmt = self._apply_ticket_kind_filter(stmt, kind)

            stmt = self._apply_recent_order(stmt)
            stmt = self._apply_pagination(stmt, limit=1, offset=offset)
            return await self._one_or_none(s, stmt)

    async def list_all(self, *, limit: Optional[int] = None, offset: int = 0) -> list[SupportTicket]:
        """Вернуть обращения клиентов в поддержку."""
        async with self._session() as s:
            stmt = select(SupportTicket)
            stmt = self._apply_recent_order(stmt)
            stmt = self._apply_pagination(stmt, limit=limit, offset=offset)
            return await self._list(s, stmt)

    async def list_open(self, *, kind: str | None = None, limit: Optional[int] = None, offset: int = 0) -> list[SupportTicket]:
        """Вернуть открытые обращения клиентов."""
        async with self._session() as s:
            stmt = select(SupportTicket)
            stmt = self._apply_status_filter(stmt, SupportTicketStatus.OPEN)
            if kind:
                stmt = self._apply_ticket_kind_filter(stmt, kind)
            stmt = self._apply_recent_order(stmt)
            stmt = self._apply_pagination(stmt, limit=limit, offset=offset)
            return await self._list(s, stmt)
        #return await self.list_by_status(SupportTicketStatus.OPEN, limit=limit, offset=offset)

    async def list_by_status(self, status: SupportTicketStatus,
                             *, limit: Optional[int] = None, offset: int = 0) -> list[SupportTicket]:
        """Вернуть обращения с указанным статусом."""
        async with self._session() as s:
            stmt = select(SupportTicket)
            stmt = self._apply_status_filter(stmt, status)
            stmt = self._apply_recent_order(stmt)
            stmt = self._apply_pagination(stmt, limit=limit, offset=offset)
            return await self._list(s, stmt)

    async def list_by_user_id(self, user_id: int,
                              *, limit: Optional[int] = None, offset: int = 0) -> list[SupportTicket]:
        """Вернуть обращения клиента."""
        async with self._session() as s:
            stmt = select(SupportTicket)
            stmt = self._apply_user_filter(stmt, user_id)
            stmt = self._apply_recent_order(stmt)
            stmt = self._apply_pagination(stmt, limit=limit, offset=offset)
            return await self._list(s, stmt)

    async def list_by_item_id(self, item_id: int,
                              *, limit: Optional[int] = None, offset: int = 0) -> list[SupportTicket]:
        """Вернуть обращения по товару."""
        async with self._session() as s:
            stmt = select(SupportTicket)
            stmt = self._apply_item_filter(stmt, item_id)
            stmt = self._apply_recent_order(stmt)
            stmt = self._apply_pagination(stmt, limit=limit, offset=offset)
            return await self._list(s, stmt)

    async def list_by_rental_id(self, rental_id: int,
                                *, limit: Optional[int] = None, offset: int = 0) -> list[SupportTicket]:
        """Вернуть обращения по заявке на аренду."""
        async with self._session() as s:
            stmt = select(SupportTicket)
            stmt = self._apply_rental_filter(stmt, rental_id)
            stmt = self._apply_recent_order(stmt)
            stmt = self._apply_pagination(stmt, limit=limit, offset=offset)
            return await self._list(s, stmt)

    async def list_by_closed_by_admin_id(self, admin_id: int,
                                         *, limit: Optional[int] = None, offset: int = 0) -> list[SupportTicket]:
        """Вернуть обращения, закрытые указанным администратором/менеджером."""
        async with self._session() as s:
            stmt = select(SupportTicket)
            stmt = self._apply_closed_by_admin_filter(stmt, admin_id)
            stmt = self._apply_recent_order(stmt)
            stmt = self._apply_pagination(stmt, limit=limit, offset=offset)
            return await self._list(s, stmt)

    async def count_open_by_user_id(self, user_id: int) -> int:
        """Вернуть количество открытых обращений клиента."""
        async with self._session() as s:
            stmt = select(func.count()).select_from(SupportTicket)
            stmt = self._apply_user_filter(stmt, user_id)
            stmt = self._apply_status_filter(stmt, SupportTicketStatus.OPEN)
            res = await s.execute(stmt)
            return int(res.scalar() or 0)

    # ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    async def close(self, *, ticket_id: int, closed_by_admin_id: int) -> bool:
        """Атомарно закрыть открытое обращение администратором/менеджером."""
        update_data = SupportTicketAdminUpdate(
            status=SupportTicketStatus.CLOSED,
            closed_at=datetime.now(timezone.utc),
            closed_by_admin_id=closed_by_admin_id
        )
        async with self._session() as s:
            stmt = update(SupportTicket)
            stmt = self._apply_id_filter(stmt, ticket_id)
            stmt = self._apply_status_filter(stmt, SupportTicketStatus.OPEN)
            stmt = stmt.values(**update_data.model_dump(exclude_unset=True))
            return await self._execute_update_commit(s, stmt)

    async def touch_admin_reply(self, *, ticket_id: int) -> bool:
        """Отметить время последнего ответа администратора/менеджера открытому по обращению.

        Зачем:
            чтобы сортировать “тикеты, которым давно не отвечали”
            чтобы видеть “последняя активность админа”
            чтобы не плодить лишние таблицы сообщений в MVP
        """
        update_data = SupportTicketAdminUpdate(admin_last_reply_at=datetime.now(timezone.utc))
        async with self._session() as s:
            stmt = update(SupportTicket)
            stmt = self._apply_id_filter(stmt, ticket_id)
            stmt = self._apply_status_filter(stmt, SupportTicketStatus.OPEN)
            stmt = stmt.values(**update_data.model_dump(exclude_unset=True))
            return await self._execute_update_commit(s, stmt)

    # ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    async def create(self, ticket_data: SupportTicketCreateInternal) -> SupportTicket:
        """Создать новое обращение клиента в поддержку."""
        payload = ticket_data.model_dump()
        async with self._session() as s:
            obj = SupportTicket(**payload)
            return await self._add_commit_refresh(s, obj)

    async def update(self, ticket_id: int, update_data: SupportTicketAdminUpdate) -> Optional[SupportTicket]:
        """Обновить обращение в поддержку."""
        async with self._session() as s:
            obj: Optional[SupportTicket] = await s.get(SupportTicket, ticket_id)
            if not obj:
                return None

            data = update_data.model_dump(exclude_unset=True)
            if not data:
                return obj

            changed = False
            for field_name, value in data.items():
                if getattr(obj, field_name) != value:
                    setattr(obj, field_name, value)
                    changed = True

            if not changed:
                return obj

            return await self._commit_refresh(s, obj)

    async def delete(self, ticket_id: int) -> bool:
        """Удалить обращение по ID."""
        async with self._session() as s:
            obj = await s.get(SupportTicket, ticket_id)
            if not obj:
                return False

            return await self._delete_commit(s, obj)