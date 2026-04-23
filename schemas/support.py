from typing import Optional
from pydantic import BaseModel, AwareDatetime, ConfigDict

from status.support_ticket_status import SupportTicketStatus


class SupportTicketCreate(BaseModel):
    """Создание тикета поддержки пользователем"""

    text: str


class SupportTicketOut(BaseModel):
    """Возврат тикета поддержки наружу (пользователь / админ)"""

    id: int

    user_id: int
    telegram_id: int
    username: Optional[str] = None

    text: str
    status: SupportTicketStatus

    closed_at: Optional[AwareDatetime] = None
    closed_by_admin_tg_id: Optional[int] = None
    admin_last_reply_at: Optional[AwareDatetime] = None

    created_at: AwareDatetime
    updated_at: AwareDatetime

    model_config = ConfigDict(from_attributes=True)


class SupportTicketCreateInternal(BaseModel):
    """Внутренняя схема для создания тикета поддержки из данных пользователя и текста обращения"""

    user_id: int
    telegram_id: int
    username: Optional[str] = None
    text: str