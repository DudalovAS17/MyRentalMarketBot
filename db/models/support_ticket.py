from __future__ import annotations

import enum
from datetime import datetime

from typing import Optional, TYPE_CHECKING
from sqlalchemy import Integer, BigInteger, String, Text, DateTime, ForeignKey, Enum as SAEnum, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.models.base import Base, TimestampMixin

"""
Поддержка — полный дизайн (MVP)

Главная идея: Поддержка = тикеты, которые создают пользователи.

Админ видит тикеты в админке, может:
    открыть тикет
    ответить пользователю
    закрыть тикет

Пользователь:
    инициирует обращение (“Написать в поддержку”)
    получает ответ
    видит статус “принято/закрыто” (минимально)
"""

if TYPE_CHECKING:
    from db.models.user import User

class SupportTicketStatus(enum.Enum):
    OPEN = "open"
    CLOSED = "closed"

class SupportTicket(Base, TimestampMixin):
    """
    MVP тикет поддержки:
    - один входящий текст от пользователя
    - админ отвечает отдельным сообщением
    """
    __tablename__ = "support_tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Ниже три поля повторяющие поля модели User - смысл этого есть, спроси у GPT :D
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    text: Mapped[str] = mapped_column(Text, nullable=False)

    # OPEN/CLOSED
    status: Mapped[SupportTicketStatus] = mapped_column(
        SAEnum(SupportTicketStatus, name="support_ticket_status"),
        nullable=False,
        default=SupportTicketStatus.OPEN,
    )

    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_by_admin_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    admin_last_reply_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="support_tickets")

    __table_args__ = (
        Index("ix_support_tickets_user_id", "user_id"),
        Index("ix_support_tickets_telegram_id", "telegram_id"),
        Index("ix_support_tickets_status", "status"),

        Index("ix_support_tickets_user_status", "user_id", "status"),
        Index("ix_support_tickets_status_created", "status", "created_at"),
    )