from pydantic import BaseModel, AwareDatetime, ConfigDict
from typing import Optional

from db.models.support_ticket import SupportTicketStatus

class SupportTicketCreate(BaseModel):
    """Создание тикета поддержки пользователем."""

    telegram_id: int
    username: Optional[str] = None
    text: str

    # Статус всегда OPEN при создании
    # status: SupportTicketStatus = SupportTicketStatus.OPEN


class SupportTicketUpdate(BaseModel):
    """Обновление тикета пользователем."""

    # пользователь может изменить только текст
    text: Optional[str] = None

    # Смена статуса должна происходить только через доменные методы: close_ticket / reopen_ticket
    # status: Optional[SupportTicketStatus] = None


class SupportTicketOut(BaseModel):
    """Возврат тикета поддержки наружу (пользователь / админ)."""

    id: int

    # Связь с пользователем
    user_id: int
    telegram_id: int
    username: Optional[str] = None

    # Содержимое тикета
    text: str
    status: SupportTicketStatus

    # Админская часть (может быть None)
    closed_at: Optional[AwareDatetime] = None
    closed_by_admin_id: Optional[int] = None
    admin_last_reply_at: Optional[AwareDatetime] = None

    created_at: AwareDatetime
    updated_at: AwareDatetime

    model_config = ConfigDict(from_attributes=True)