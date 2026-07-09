from typing import Optional
from pydantic import BaseModel, AwareDatetime, ConfigDict, Field

from status.support_ticket_status import SupportTicketStatus, SupportMessageSenderType


class SupportTicketCreate(BaseModel):
    """Клиентская схема создания обращения в поддержку."""

    text: str = Field(..., min_length=1)
    subject: Optional[str] = Field(None, max_length=150)
    item_id: Optional[int] = None
    rental_id: Optional[int] = None


class SupportTicketOut(BaseModel):
    """Возврат обращения в поддержку наружу (клиент / админ)."""

    id: int
    user_id: int

    subject: Optional[str] = None
    item_id: Optional[int] = None
    rental_id: Optional[int] = None

    text: str
    status: SupportTicketStatus

    closed_at: Optional[AwareDatetime] = None
    closed_by_admin_id: Optional[int] = None
    admin_last_reply_at: Optional[AwareDatetime] = None

    created_at: AwareDatetime
    updated_at: AwareDatetime

    model_config = ConfigDict(from_attributes=True)


# ─────────────────────────────────────── Support Ticket Internal ──────────────────────────────────────────────────────
class SupportTicketCreateInternal(SupportTicketCreate):
    """Внутренняя схема создания обращения с уже определённым клиентом."""

    user_id: int


# ─────────────────────────────────────── Support Ticket Admin ─────────────────────────────────────────────────────────
class SupportTicketAdminUpdate(BaseModel):
    """Схема для админского обновления обращения в поддержку."""

    status: Optional[SupportTicketStatus] = None
    closed_at: Optional[AwareDatetime] = None
    closed_by_admin_id: Optional[int] = None
    admin_last_reply_at: Optional[AwareDatetime] = None

# в сервисе нужно соблюдать правило: если закрываем тикет → closed_at и closed_by_admin_id должны быть заполнены вместе


# ─────────────────────────────────── Логика Support Message ───────────────────────────────────────────────────────
class SupportMessageOut(BaseModel):
    """Сообщение внутри тикета поддержки."""

    id: int
    ticket_id: int
    sender_type: SupportMessageSenderType
    sender_user_id: Optional[int] = None
    sender_admin_id: Optional[int] = None
    text: str
    created_at: AwareDatetime
    updated_at: AwareDatetime

    model_config = ConfigDict(from_attributes=True)