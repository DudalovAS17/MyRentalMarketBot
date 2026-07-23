import logging
from typing import Optional
from datetime import datetime, timezone
from dataclasses import dataclass

from db.repositories.support_ticket import SupportTicketRepository
from services.admin_directory_service import AdminDirectoryService

from schemas.support import SupportTicketOut, SupportTicketCreateInternal, SupportMessageOut
from status.support_ticket_status import SupportTicketStatus
from utils.errors import NotFoundError, ConflictError, ValidationError
from utils.domain_exceptions import TicketAlreadyOpen

logger = logging.getLogger(__name__)

PAGE_SIZE = 8

# пока не используется
@dataclass(frozen=True)
class SupportStartContext:
    """Business context for starting a support flow."""
    kind: str
    subject: str | None
    open_ticket: SupportTicketOut | None


class SupportService:
    """Сервис для работы с обращениями клиентов в поддержку."""

    def __init__(self, support_repo: SupportTicketRepository, admin_directory_service: AdminDirectoryService):
        self.repo = support_repo
        self.admin_directory_service = admin_directory_service

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

    @staticmethod
    def _to_message_out(message) -> SupportMessageOut:
        return SupportMessageOut.model_validate(message)

    @classmethod
    def _to_message_out_list(cls, messages) -> list[SupportMessageOut]:
        return [cls._to_message_out(message) for message in messages]

    # ─────────────────────────────────────── Business validation ─────────────────────────────────────────────────────
    # не используется
    @staticmethod
    def normalize_required_text(value: str, field_name: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValidationError(f"{field_name} не может быть пустым")
        return normalized

    async def _ensure_user_has_no_open_ticket(self, user_id: int, *, kind: str | None = None) -> None:
        open_ticket = await self.repo.get_open_by_user_id(user_id, kind=kind)
        if open_ticket:
            raise TicketAlreadyOpen(ticket_id=open_ticket.id)

    @staticmethod
    def ticket_kind_for_data(ticket_data: SupportTicketCreateInternal) -> str:
        """Определить клиентский контур обращения для ограничения дублей."""
        if ticket_data.rental_id is not None:
            return "rentals"
        if ticket_data.item_id is not None:
            return "items"
        return "general"

    # То же самое, но через id
    @staticmethod
    def ticket_kind_for_context(*, rental_id: int | None = None, item_id: int | None = None) -> str:
        """Определить контур обращения по связанному объекту."""
        if rental_id is not None:
            return "rentals"
        if item_id is not None:
            return "items"
        return "general"

    @staticmethod
    def subject_for_context(*, rental_id: int | None = None, item_id: int | None = None) -> str | None:
        """Сформировать служебную тему обращения по контексту."""
        if item_id is not None:
            return f"Вопрос по товару #{item_id}"
        if rental_id is not None:
            return f"Заявка на аренду #{rental_id}"
        return None

    @staticmethod
    def is_open_ticket(ticket: SupportTicketOut) -> bool:
        """Проверить, что тикет открыт."""
        return ticket.status == SupportTicketStatus.OPEN

    @classmethod
    def can_append_user_reply(cls, ticket: SupportTicketOut, *, user_id: int) -> bool:
        """Проверить, может ли клиент добавить ответ в тикет."""
        return ticket.user_id == user_id and cls.is_open_ticket(ticket)

    # @staticmethod
    # def admin_ticket_actions_for_status(status: SupportTicketStatus) -> tuple[str, ...]:
    #     """Вернуть допустимые admin UI-actions для тикета поддержки."""
    #     if status == SupportTicketStatus.OPEN:
    #         return "reply", "close"
    #     return ()

    @staticmethod
    def validate_ticket_context(ticket_data: SupportTicketCreateInternal) -> None:
        """Проверить, что обращение связано не более чем с одним бизнес-контекстом."""
        if ticket_data.item_id is not None and ticket_data.rental_id is not None:
            raise ValidationError("Обращение нельзя одновременно связать с товаром и заявкой аренды")

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

        self.validate_ticket_context(ticket_data)
        # normalized_text = self.normalize_required_text(ticket_data.text, "Сообщение")
        # normalized_subject = ticket_data.subject.strip() if ticket_data.subject else None
        # ticket_data = ticket_data.model_copy(update={"text": normalized_text, "subject": normalized_subject})

        await self._ensure_user_has_no_open_ticket(
            ticket_data.user_id,
            kind=self.ticket_kind_for_data(ticket_data),
        )

        ticket = await self.repo.create(ticket_data)
        return self._to_out(ticket)

    # ─────────────────────────────────────────── Admin actions ────────────────────────────────────────────────────────
    async def close_ticket_by_admin(self, *, ticket_id: int, closed_by_admin_id: int = None, strict: bool = False) -> bool:
        """Закрыть тикет обращения администратором"""
        if closed_by_admin_id is None:
            raise ValidationError("Некорректный ID сотрудника")

        await self.admin_directory_service.ensure_active_admin_by_id(closed_by_admin_id)

        ticket = await self.get_ticket_by_id(ticket_id)
        if not ticket:
            if strict:
                raise NotFoundError(f"Обращение в поддержку не найдено: id={ticket_id}")
            return False
        if not self.is_open_ticket(ticket):
            if strict:
                raise ConflictError("Обращение в поддержку уже закрыто")
            return False

        ok = await self.repo.close(
            ticket_id=ticket_id,
            closed_by_admin_id=closed_by_admin_id,
            closed_at=datetime.now(timezone.utc),
        )
        if not ok and strict:
            raise ConflictError("Не удалось закрыть обращение в поддержку")

        if ok:
            logger.info("Обращение в поддержку закрыто: id=%s admin_id=%s", ticket_id, closed_by_admin_id)
        return ok


    # ─────────────────────────────────────────── Service actions ──────────────────────────────────────────────────────
    async def append_user_reply(self, *, ticket_id: int, user_id: int, reply_text: str, strict: bool = False) -> \
    Optional[SupportTicketOut]:
        """Добавить сообщение клиента в существующий открытый тикет."""
        normalized = self.normalize_required_text(reply_text, "Ответ")
        ticket = await self.get_ticket_by_id(ticket_id)
        if not ticket or ticket.user_id != user_id:
            if strict:
                raise NotFoundError(f"Открытое обращение в поддержку не найдено: id={ticket_id}")
            return None
        if not self.is_open_ticket(ticket):
            if strict:
                raise ConflictError("Обращение в поддержку уже закрыто")
            return None

        obj = await self.repo.add_user_message(ticket_id=ticket_id, sender_user_id=user_id, text=normalized)
        if not obj:
            if strict:
                raise ConflictError("Не удалось сохранить сообщение в поддержку")
            return None

        #logger.info("Клиент добавил сообщение в тикет поддержки: id=%s user_id=%s", ticket_id, user_id)
        return self._to_out(obj)

    async def mark_admin_replied(self, *, ticket_id: int, strict: bool = False) -> bool:
        """Отметить, что администратор/менеджер ответил по обращению."""
        ticket = await self.get_ticket_by_id(ticket_id)
        if not ticket:
            if strict:
                raise NotFoundError(f"Обращение в поддержку не найдено: id={ticket_id}")
            return False
        if not self.is_open_ticket(ticket):
            if strict:
                raise ConflictError("Обращение в поддержку уже закрыто")
            return False

        ok = await self.repo.touch_admin_reply(ticket_id=ticket_id, replied_at=datetime.now(timezone.utc))
        if not ok and strict:
            raise ConflictError("Не удалось отметить ответ сотрудника")

        if ok:
            logger.info("По обращению в поддержку отмечен ответ сотрудника: id=%s", ticket_id)
        return ok


    # ─────────────────────────────────── Логика Support Message ───────────────────────────────────────────────────────
    async def list_ticket_messages(self, ticket_id: int) -> list[SupportMessageOut]:
        """Вернуть сохранённую историю сообщений тикета."""
        messages = await self.repo.list_messages(ticket_id)
        return self._to_message_out_list(messages)

    async def save_admin_reply(self, *, ticket_id: int, sender_admin_id: int, reply_text: str, strict: bool = False) -> Optional[SupportTicketOut]:
        """Сохранить ответ админа в истории сообщений и отметить активность."""

        await self.admin_directory_service.ensure_active_admin_by_id(sender_admin_id)

        normalized = self.normalize_required_text(reply_text, "Ответ")
        ticket = await self.get_ticket_by_id(ticket_id)
        if not ticket:
            if strict:
                raise NotFoundError(f"Обращение в поддержку не найдено: id={ticket_id}")
            return None
        if not self.is_open_ticket(ticket):
            if strict:
                raise ConflictError("Обращение в поддержку уже закрыто")
            return None

        obj = await self.repo.add_admin_message(
            ticket_id=ticket_id,
            sender_admin_id=sender_admin_id,
            text=normalized,
            replied_at=datetime.now(timezone.utc),
        )
        if not obj:
            if strict:
                raise ConflictError("Не удалось сохранить ответ сотрудника")
            return None

        logger.info("Ответ сотрудника сохранён в истории поддержки: id=%s admin_id=%s", ticket_id, sender_admin_id)
        return self._to_out(obj)