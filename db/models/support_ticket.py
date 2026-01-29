import enum
from datetime import datetime

from sqlalchemy import Integer, String, Text, DateTime, ForeignKey, Enum as SAEnum, Index, Any
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.models.base import Base, TimestampMixin, ReprMixin, DictMixin

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

class SupportTicketStatus(enum.Enum):
    OPEN = "open"
    CLOSED = "closed"

class SupportTicket(Base, TimestampMixin, ReprMixin, DictMixin):
    """
    MVP тикет поддержки:
    - один входящий текст от пользователя
    - админ отвечает отдельным сообщением
    """
    __tablename__ = "support_tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)

    telegram_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)

    text: Mapped[str] = mapped_column(Text, nullable=False)

    status: Mapped[SupportTicketStatus] = mapped_column(             # OPEN/CLOSED
        SAEnum(SupportTicketStatus, name="support_ticket_status"),
        nullable=False,
        default=SupportTicketStatus.OPEN,
        index=True,
    )

    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Mapped[DateTime | None]
    closed_by_admin_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    admin_last_reply_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="support_tickets")

    __table_args__ = (
        Index("ix_support_tickets_user_status", "user_id", "status"),
        Index("ix_support_tickets_status_created", "status", "created_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<SupportTicket id={self.id} user_id={self.user_id} "
            f"status={getattr(self.status, 'value', self.status)}>"
        )

    def to_dict(self) -> dict[str, Any]:
        d = DictMixin.to_dict(self)

        # # Enum -> str
        d["status"] = self.status.value if isinstance(self.status, enum.Enum) else self.status # else d.get("status")

        # datetime -> ISO
        for k in ("created_at", "updated_at", "closed_at", "admin_last_reply_at"):
            if isinstance(d.get(k), datetime):
                d[k] = d[k].isoformat()

        return d