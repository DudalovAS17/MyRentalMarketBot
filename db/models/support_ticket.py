from __future__ import annotations

from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import Integer,  CheckConstraint, BigInteger, Text, DateTime, ForeignKey, Enum as SAEnum, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.models.base import Base, TimestampMixin
from status.support_ticket_status import SupportTicketStatus

if TYPE_CHECKING:
    from db.models.user import User


class SupportTicket(Base, TimestampMixin):
    """MVP тикет поддержки:
    - один входящий текст от пользователя
    - админ отвечает отдельным сообщением
    """
    __tablename__ = "support_tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # тикет принадлежит пользователю
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)

    # основное содержание обращения
    text: Mapped[str] = mapped_column(Text, nullable=False)

    # OPEN/CLOSED
    status: Mapped[SupportTicketStatus] = mapped_column(
        SAEnum(SupportTicketStatus, name="support_ticket_status"),
        nullable=False,
        default=SupportTicketStatus.OPEN,
    )

    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_by_admin_tg_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    # когда админ в последний раз отвечал по тикету
    admin_last_reply_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # ------- Отношения | связи --------

    # тикет знает своего пользователя | пользователь знает свои тикеты
    user: Mapped["User"] = relationship("User", back_populates="support_tickets")

    __table_args__ = (
        Index("ix_support_tickets_user_id", "user_id"),
        Index("ix_support_tickets_telegram_id", "telegram_id"),
        Index("ix_support_tickets_status", "status"),

        # Нельзя закрыть тикет без даты закрытия (и наоборот) (либо оба closed_at и closed_by_admin_tg_id пустые, либо оба заполнены)
        CheckConstraint(
            "(closed_at IS NULL AND closed_by_admin_tg_id IS NULL) "
            "OR (closed_at IS NOT NULL AND closed_by_admin_tg_id IS NOT NULL)",
            name="ck_support_tickets_closed_fields_consistent",
        ),

        # Частые запросы в админке: "открытые тикеты" и "сортировка по дате"
        Index("ix_support_tickets_user_status", "user_id", "status"),
        Index("ix_support_tickets_status_created", "status", "created_at"),
    )