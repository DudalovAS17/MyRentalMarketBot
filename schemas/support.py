from pydantic import BaseModel, AwareDatetime, ConfigDict
from typing import Optional

from db.models.support_ticket import SupportTicketStatus

class SupportTicketCreate(BaseModel):
    """Создание тикета поддержки пользователем."""
    telegram_id: int # Убираем?
    username: Optional[str] = None # Убираем?
    text: str


# Убираем?
class SupportTicketUpdate(BaseModel):
    """Обновление тикета пользователем."""
    # пользователь может изменить только текст
    text: Optional[str] = None # Убираем?


class SupportTicketOut(BaseModel):
    """Возврат тикета поддержки наружу (пользователь / админ)."""
    id: int

    # Связь с пользователем
    user_id: int
    telegram_id: int
    username: Optional[str] = None

    # Содержимое тикета
    text: str
    status: SupportTicketStatus # OPEN/CLOSED

    # Админская часть (может быть None)
    closed_at: Optional[AwareDatetime] = None
    closed_by_admin_tg_id: Optional[int] = None
    admin_last_reply_at: Optional[AwareDatetime] = None

    created_at: AwareDatetime
    updated_at: AwareDatetime

    model_config = ConfigDict(from_attributes=True)


# Статус всегда OPEN при создании (status: SupportTicketStatus = SupportTicketStatus.OPEN)

# Смена статуса должна происходить только через доменные методы: close_ticket / reopen_ticket
# status: Optional[SupportTicketStatus] = None


class SupportTicketCreateInternal(BaseModel):
    user_id: int
    telegram_id: int
    username: Optional[str] = None
    text: str