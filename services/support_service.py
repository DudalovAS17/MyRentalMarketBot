import logging
from typing import Optional

from db.repositories.support_ticket import SupportTicketRepository

from schemas.support import SupportTicketOut, SupportTicketCreateInternal
from utils.errors import NotFoundError, ConflictError
from utils.domain_exceptions import TicketAlreadyOpen

logger = logging.getLogger(__name__)

PAGE_SIZE = 8

class SupportService:
    """Сервис для работы с тикетами поддержки"""

    def __init__(self, support_repo: SupportTicketRepository):
        self.repo = support_repo

    # ────────────────────────────────────────── Read methods ──────────────────────────────────────────────────────────
    async def get_ticket_by_id(self, ticket_id: int, *, strict: bool = False) -> Optional[SupportTicketOut]:
        """Вернуть тикет поддержки по его id"""
        obj = await self.repo.get_by_id(ticket_id)
        if not obj:
            if strict:
                raise NotFoundError(f"Тикет обращения не найден: id={ticket_id}")
            return None

        return SupportTicketOut.model_validate(obj)

    async def list_open_tickets(self, page: int) -> tuple[list[SupportTicketOut], bool]:
        """Вернуть список открытых тикетов с пагинацией"""
        safe_page = max(1, page)
        limit = PAGE_SIZE
        offset = (safe_page - 1) * limit

        tickets = await self.repo.list_open(limit=limit + 1, offset=offset)

        has_next = len(tickets) > limit
        dtos = [SupportTicketOut.model_validate(t) for t in tickets[:limit]]
        return dtos, has_next

    async def get_open_ticket_by_user(self, user_id: int, *, strict: bool = False) -> Optional[SupportTicketOut]:
        """Вернуть открытый тикет пользователя, если он существует"""
        obj = await self.repo.get_open_by_user_id(user_id)
        if not obj:
            if strict:
                raise NotFoundError(f"Открытый тикет обращения не найден для user_id={user_id}")
            return None

        return SupportTicketOut.model_validate(obj)

    # ─────────────────────────────────────────── write methods ────────────────────────────────────────────────────────
    async def create(self, *, ticket_data: SupportTicketCreateInternal) -> SupportTicketOut:
        """Создаёт тикет, если у пользователя нет OPEN тикета"""
        open_ticket = await self.repo.get_open_by_user_id(ticket_data.user_id)
        if open_ticket:
            raise TicketAlreadyOpen(ticket_id=open_ticket.id)

        ticket = await self.repo.create(ticket_data)
        return SupportTicketOut.model_validate(ticket)

    # ─────────────────────────────────────────── Admin admin_actions ────────────────────────────────────────────────────────
    async def close_ticket_by_admin(self, *, ticket_id: int, admin_tg_id: int, strict: bool = False) -> bool:
        """Закрыть тикет обращения администратором"""
        ok = await self.repo.close(ticket_id=ticket_id, admin_tg_id=admin_tg_id)
        if not ok and strict:
            raise ConflictError("Тикет обращения не найден или уже закрыт")

        return ok

    # ─────────────────────────────────────────── Service admin_actions ────────────────────────────────────────────────────────
    async def mark_admin_replied(self, *, ticket_id: int, strict: bool = False) -> bool:
        """Отметить, что администратор ответил по тикету"""
        ok = await self.repo.touch_admin_reply(ticket_id=ticket_id)
        if not ok and strict:
            raise NotFoundError(f"Тикет обращения не найден: id={ticket_id}")
        return ok