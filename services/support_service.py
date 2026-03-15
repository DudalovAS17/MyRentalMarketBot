import logging
from typing import Optional

from db.repositories.support_ticket import SupportTicketRepository
from schemas.support import SupportTicketOut, SupportTicketCreateInternal
from utils.errors import NotFoundError, ConflictError
from utils.domain_exceptions import TicketAlreadyOpen

logger = logging.getLogger(__name__)

PAGE_SIZE = 8

class SupportService:

    def __init__(self, support_repo: SupportTicketRepository):
        self.repo = support_repo

    async def get_ticket(self, ticket_id: int, *, strict: bool = False) -> Optional[SupportTicketOut]:
        obj = await self.repo.get_by_id(ticket_id)
        if not obj:
            if strict:
                raise NotFoundError(f"Тикет обращения не найден: id={ticket_id}")
            return None

        return SupportTicketOut.model_validate(obj)

    async def list_open_tickets(self, page: int) -> tuple[list[SupportTicketOut], bool]:
        page = max(1, page)
        limit = PAGE_SIZE
        offset = (page - 1) * limit

        tickets = await self.repo.list_open(limit=limit + 1, offset=offset)

        has_next = len(tickets) > limit
        dtos = [SupportTicketOut.model_validate(t) for t in tickets[:limit]]
        return dtos, has_next # есть ли следующая страница

    async def get_open_ticket_by_user(self, user_id: int, *, strict: bool = False) -> Optional[SupportTicketOut]:
        obj = await self.repo.get_open_by_user_id(user_id)
        if not obj:
            if strict:
                raise NotFoundError(f"Тикет обращения не найден") # : id={obj.id}
            return None

        return SupportTicketOut.model_validate(obj)

    async def close_ticket(self, *, ticket_id: int, admin_id: int, strict: bool = False) -> bool:
        ok = await self.repo.close(ticket_id=ticket_id, admin_id=admin_id)
        if not ok and strict:
            raise ConflictError("Тикет обращения не найден или уже закрыт")
        return ok

    async def mark_admin_replied(self, *, ticket_id: int, strict: bool = False) -> bool:
        ok = await self.repo.touch_admin_reply(ticket_id=ticket_id)
        if not ok and strict:
            raise NotFoundError(f"Тикет обращения не найден: id={ticket_id}")
        return ok

    # -------------------------------------------------------------------------------------------------------
    async def create_ticket(self, *, ticket_data: SupportTicketCreateInternal) -> SupportTicketOut:
        """Создаёт тикет, если у пользователя нет OPEN тикета"""
        open_ticket = await self.repo.get_open_by_user_id(ticket_data.user_id)
        if open_ticket:
            raise TicketAlreadyOpen(ticket_id=open_ticket.id)

        ticket = await self.repo.create(ticket_data)
        return SupportTicketOut.model_validate(ticket)
    # -------------------------------------------------------------------------------------------------------