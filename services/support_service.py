import logging
from typing import Optional, Any, List

from db.models.support_ticket import SupportTicket, SupportTicketStatus
from db.repositories.support_ticket import SupportTicketRepository
from schemas.support import SupportTicketCreate, SupportTicketUpdate
from services.user_service import UserService

from utils.domain_exceptions import TicketAlreadyOpen

logger = logging.getLogger(__name__)


class SupportService:
    PAGE_SIZE = 8

    def __init__(self, support_repo: SupportTicketRepository):
        self.repo = support_repo

    async def create_ticket(self, ticket_data: SupportTicketCreate) -> SupportTicket:
        """Создаёт тикет, если у пользователя нет OPEN тикета"""
        open_ticket = await self.repo.get_open_by_user_id(ticket_data.user_id)
        if open_ticket:
            raise TicketAlreadyOpen(ticket_id=open_ticket.id)

        ticket = await self.repo.create(ticket_data)
        return ticket

    async def get_ticket(self, ticket_id: int) -> SupportTicket | None: # Optional[SupportTicket]:
        return await self.repo.get_by_id(ticket_id)

    async def list_open_tickets(self, page: int) -> tuple[list[SupportTicket], bool]:
        page = max(1, page)
        limit = self.PAGE_SIZE
        offset = (page - 1) * limit

        tickets = await self.repo.list_open(limit=limit + 1, offset=offset)
        has_next = len(tickets) > limit
        return tickets[:limit], has_next
        # (list[SupportTicket], bool) = (список_тикетов_текущей_страницы, есть_ли_следующая_страница)

    async def get_open_ticket_by_user(self, user_id: int):
        return await self.repo.get_open_by_user_id(user_id)

    async def close_ticket(self, *, ticket_id: int, admin_id: int) -> bool:
        return await self.repo.close(ticket_id=ticket_id, admin_id=admin_id)

    async def mark_admin_replied(self, *, ticket_id: int) -> None:
        await self.repo.touch_admin_reply(ticket_id=ticket_id)


