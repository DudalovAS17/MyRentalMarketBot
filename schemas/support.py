from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from db.models.support_ticket import SupportTicketStatus

class SupportTicketCreate(BaseModel):
    user_id: int
    telegram_id: int
    username: str | None
    text: str
    status: SupportTicketStatus = SupportTicketStatus.OPEN # убираем?
    # Статус всегда OPEN при создании — это инвариант домена, а не входной параметр.


class SupportTicketUpdate(BaseModel):
    text: Optional[str] = None
    #status: Optional[SupportTicketStatus] = None
    # Смена статуса должна происходить только через доменные методы: close_ticket / reopen_ticket


class SupportTicketOut(BaseModel):
    id: int
    user_id: int
    telegram_id: int
    username: str | None
    text: str
    status: SupportTicketStatus
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    #closed_at: Optional[datetime] = None
    #closed_by_admin_id: Optional[datetime] = None
    #admin_last_reply_at: Optional[datetime] = None

    class Config:
        from_attributes = True