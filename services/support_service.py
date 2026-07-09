import logging
from typing import Optional

from db.repositories.support_ticket import SupportTicketRepository

from schemas.support import SupportTicketOut, SupportTicketCreateInternal
from utils.errors import NotFoundError, ConflictError, ValidationError
from utils.domain_exceptions import TicketAlreadyOpen

logger = logging.getLogger(__name__)

PAGE_SIZE = 8

class SupportService:
    """Сервис для работы с обращениями клиентов в поддержку."""

    def __init__(self, support_repo: SupportTicketRepository):
        self.repo = support_repo

    # ────────────────────────────────────────── DTO helpers ──────────────────────────────────────────────────────────
    @staticmethod
    def _to_out(ticket) -> SupportTicketOut:
        return SupportTicketOut.model_validate(ticket)

    @classmethod
    def _to_out_list(cls, tickets) -> list[SupportTicketOut]:
        return [cls._to_out(ticket) for ticket in tickets]

    @staticmethod
    def _page_window(page: int, *, page_size: int = PAGE_SIZE) -> tuple[int, int]:
        safe_page = max(1, page)
        limit = page_size
        offset = (safe_page - 1) * limit
        return limit, offset

    # ─────────────────────────────────────── Business validation ─────────────────────────────────────────────────────
    # не используется
    @staticmethod
    def _normalize_required_text(value: str, field_name: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValidationError(f"{field_name} не может быть пустым")
        return normalized

    @staticmethod
    def ticket_kind_for_data(ticket_data: SupportTicketCreateInternal) -> str:
        """Определить клиентский контур обращения для ограничения дублей."""
        if ticket_data.rental_id is not None:
            return "rentals"
        if ticket_data.item_id is not None:
            return "items"
        return "general"

    async def _ensure_user_has_no_open_ticket(self, user_id: int, *, kind: str | None = None) -> None:
        open_ticket = await self.repo.get_open_by_user_id(user_id, kind=kind)
        if open_ticket:
            raise TicketAlreadyOpen(ticket_id=open_ticket.id)

    # ────────────────────────────────────────── Read methods ──────────────────────────────────────────────────────────
    async def get_ticket_by_id(self, ticket_id: int, *, strict: bool = False) -> Optional[SupportTicketOut]:
        """Вернуть обращение в поддержку по его ID."""
        obj = await self.repo.get_by_id(ticket_id)
        if not obj:
            if strict:
                raise NotFoundError(f"Обращение в поддержку не найдено: id={ticket_id}")
            return None

        return self._to_out(obj)

    async def list_open_tickets(self, page: int, *, kind: str | None = None) -> tuple[list[SupportTicketOut], bool]:
        """Вернуть список открытых обращений в поддержку с пагинацией."""
        limit, offset = self._page_window(page)
        tickets = await self.repo.list_open(kind=kind, limit=limit + 1, offset=offset)

        has_next = len(tickets) > limit
        return self._to_out_list(tickets[:limit]), has_next

    async def get_open_ticket_by_user(self, user_id: int, *, kind: str | None = None, strict: bool = False) -> Optional[SupportTicketOut]:
        """Вернуть открытое обращение пользователя, если оно существует."""
        obj = await self.repo.get_open_by_user_id(user_id, kind=kind)
        if not obj:
            if strict:
                raise NotFoundError(f"Открытое обращение в поддержку не найдено для user_id={user_id}")
            return None

        return self._to_out(obj)

    # ─────────────────────────────────────────── write methods ────────────────────────────────────────────────────────
    async def create(self, *, ticket_data: SupportTicketCreateInternal) -> SupportTicketOut:
        """Создать обращение, если у пользователя нет открытого обращения в этом контуре."""
        await self._ensure_user_has_no_open_ticket(
            ticket_data.user_id,
            kind=self.ticket_kind_for_data(ticket_data),
        )

        ticket = await self.repo.create(ticket_data)
        return self._to_out(ticket)

    # ─────────────────────────────────────────── Admin actions ────────────────────────────────────────────────────────
    async def close_ticket_by_admin(self, *, ticket_id: int, closed_by_admin_id: int = None, strict: bool = False) -> bool:
        """Закрыть тикет обращения администратором"""
        ok = await self.repo.close(ticket_id=ticket_id, closed_by_admin_id=closed_by_admin_id)
        if not ok and strict: # тогда: тикета нет / тикет есть, но он уже CLOSED
            raise ConflictError("Обращение в поддержку не найдено или уже закрыто")

        if ok:
            logger.info("Обращение в поддержку закрыто: id=%s admin_id=%s", ticket_id, closed_by_admin_id)
        return ok


    # ─────────────────────────────────────────── Service actions ──────────────────────────────────────────────────────
    async def append_user_reply(self, *, ticket_id: int, user_id: int, reply_text: str, strict: bool = False) -> \
    Optional[SupportTicketOut]:
        """Добавить сообщение клиента в существующий открытый тикет."""
        normalized = self._normalize_required_text(reply_text, "Ответ")
        ticket = await self.get_ticket_by_id(ticket_id)
        if not ticket or ticket.user_id != user_id:
            if strict:
                raise NotFoundError(f"Открытое обращение в поддержку не найдено: id={ticket_id}")
            return None

        obj = await self.repo.append_user_reply(ticket_id=ticket_id, reply_text=normalized)
        if not obj:
            if strict:
                raise ConflictError("Обращение в поддержку не найдено или уже закрыто")
            return None

        #logger.info("Клиент добавил сообщение в тикет поддержки: id=%s user_id=%s", ticket_id, user_id)
        return self._to_out(obj)

    async def mark_admin_replied(self, *, ticket_id: int, strict: bool = False) -> bool:
        """Отметить, что администратор/менеджер ответил по обращению."""
        ok = await self.repo.touch_admin_reply(ticket_id=ticket_id)
        if not ok and strict:
            raise NotFoundError(f"Обращение в поддержку не найдено: id={ticket_id}")

        if ok:
            logger.info("По обращению в поддержку отмечен ответ сотрудника: id=%s", ticket_id)
        return ok