from __future__ import annotations

from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import Integer, String, CheckConstraint, Text, DateTime, ForeignKey, Enum as SAEnum, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.models.base import Base, TimestampMixin, enum_values
from status.support_ticket_status import SupportTicketStatus, SupportMessageSenderType

if TYPE_CHECKING:
    from db.models.user import User
    from db.models.admins import Admin
    from db.models.item import Item
    from db.models.rental import Rental

class SupportTicket(Base, TimestampMixin):
    """Обращение клиента в поддержку"""

    __tablename__ = "support_tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # тикет принадлежит пользователю
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)

    # основное содержание обращения
    text: Mapped[str] = mapped_column(Text, nullable=False)
    # тема обращения: короткая тема для админки
    subject: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)

    item_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("items.id", ondelete="SET NULL"),
        nullable=True,
    )

    # если пользователь пишет по уже созданной заявке, тикет будет связан с ней
    rental_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("rentals.id", ondelete="SET NULL"),
        nullable=True,
    )

    # OPEN/CLOSED
    status: Mapped[SupportTicketStatus] = mapped_column(
        SAEnum(SupportTicketStatus, name="support_ticket_status", values_callable=enum_values),
        nullable=False,
        default=SupportTicketStatus.OPEN,
    )

    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    #closed_by_admin_tg_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    closed_by_admin_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("admins.id", ondelete="SET NULL"),
        nullable=True,
    )

    # когда админ в последний раз отвечал по тикету
    admin_last_reply_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


    # ------- Отношения | связи --------

    # тикет знает своего пользователя | пользователь знает свои тикеты
    user: Mapped["User"] = relationship("User", back_populates="support_tickets")

    item: Mapped[Optional["Item"]] = relationship("Item", back_populates="support_tickets")
    rental: Mapped[Optional["Rental"]] = relationship("Rental", back_populates="support_tickets")

    messages: Mapped[list["SupportMessage"]] = relationship(
        "SupportMessage",
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="SupportMessage.created_at",
    )

    closed_by_admin: Mapped[Optional["Admin"]] = relationship(
        "Admin",
        foreign_keys=[closed_by_admin_id],
        back_populates="closed_support_tickets",
    )

    __table_args__ = (
        Index("ix_support_tickets_user_id", "user_id"),
        #Index("ix_support_tickets_telegram_id", "telegram_id"),
        Index("ix_support_tickets_status", "status"),

        # Нельзя закрыть тикет без даты закрытия (и наоборот) (либо оба closed_at и closed_by_admin_tg_id пустые, либо оба заполнены)
        CheckConstraint(
            "(closed_at IS NULL AND closed_by_admin_id IS NULL) " # closed_by_admin_tg_id
            "OR (closed_at IS NOT NULL AND closed_by_admin_id IS NOT NULL)", # closed_by_admin_tg_id
            name="ck_support_tickets_closed_fields_consistent",
        ),

        # Частые запросы в админке: "открытые тикеты" и "сортировка по дате"
        Index("ix_support_tickets_user_status", "user_id", "status"),
        Index("ix_support_tickets_status_created", "status", "created_at"),

        Index("ix_support_tickets_item_id", "item_id"),
        Index("ix_support_tickets_rental_id", "rental_id"),
        Index("ix_support_tickets_closed_by_admin_id", "closed_by_admin_id"),
        Index("ix_support_tickets_request_status", "rental_id", "status"),
    )


class SupportMessage(Base, TimestampMixin):
    """Сообщение в обращении поддержки для MVP-истории переписки."""

    __tablename__ = "support_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("support_tickets.id", ondelete="CASCADE"), nullable=False)
    sender_type: Mapped[SupportMessageSenderType] = mapped_column(
        SAEnum(SupportMessageSenderType, name="support_message_sender_type", values_callable=enum_values),
        nullable=False,
    )
    sender_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    sender_admin_id: Mapped[Optional[int]] = mapped_column(ForeignKey("admins.id", ondelete="SET NULL"), nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)

    ticket: Mapped["SupportTicket"] = relationship("SupportTicket", back_populates="messages")

    __table_args__ = (
        CheckConstraint(
            "(sender_type = 'user' AND sender_user_id IS NOT NULL AND sender_admin_id IS NULL) "
            "OR (sender_type = 'admin' AND sender_admin_id IS NOT NULL AND sender_user_id IS NULL) "
            "OR (sender_type = 'system')",
            name="ck_support_messages_sender_consistent",
        ),
        Index("ix_support_messages_ticket_created", "ticket_id", "created_at"),
        Index("ix_support_messages_sender_user_id", "sender_user_id"),
        Index("ix_support_messages_sender_admin_id", "sender_admin_id"),
    )
