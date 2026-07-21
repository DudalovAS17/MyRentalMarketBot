from __future__ import annotations

from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import Integer, String, Enum as SAEnum, Index, DateTime, Text, ForeignKey, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.models.base import Base, TimestampMixin, enum_values
from status.user_status import AccountStatus

if TYPE_CHECKING:
    #from db.models.item import Item
    from db.models.rental import Rental
    from db.models.support_ticket import SupportTicket
    from db.models.admins import Admin
    from db.models.review import Review

class User(Base, TimestampMixin):
    """Клиент."""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # уникальный телеграм-id
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True)

    # профиль
    username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # флаг отправки сообщений: полезно для рассылок и уведомлений
    #can_receive_messages: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Добавить язык пользователя
    language_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    account_status: Mapped[AccountStatus] = mapped_column(
        SAEnum(AccountStatus, name="account_status", values_callable=enum_values),
        nullable=False,
        default=AccountStatus.ACTIVE
    )

    # аудит админов (когда, кто, зачем)
    banned_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    banned_by_admin_id: Mapped[Optional[int]] = mapped_column(ForeignKey("admins.id", ondelete="SET NULL"), nullable=True)
    ban_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


    # ------- Отношения | связи --------

    # один пользователь может оставить много заявок на аренду
    rentals: Mapped[list["Rental"]] = relationship("Rental", back_populates="user")

    # связь с корзиной: один пользователь может добавить несколько товаров в корзину
    # cart_items: Mapped[list["CartItem"]] = relationship(
    #     "CartItem",
    #     back_populates="user",
    #     cascade="all, delete-orphan",
    #     single_parent=True,
    # )

    support_tickets: Mapped[list["SupportTicket"]] = relationship("SupportTicket", back_populates="user")
    banned_by_admin: Mapped[Optional["Admin"]] = relationship("Admin", foreign_keys=[banned_by_admin_id])
    reviews: Mapped[list["Review"]] = relationship("Review", back_populates="user")

    __table_args__ = (
        Index("ix_users_account_status", "account_status"),
        Index("ix_users_username", "username"),

        Index("ix_users_telegram_id", "telegram_id"),
        Index("ix_users_phone", "phone"),
        #Index("ix_users_can_receive_messages", "can_receive_messages"),
    )


""" Дополнительные будущие поля:

top_up_amount — сколько всего денег пользователь пополнил.
consume_records — сколько всего денег пользователь потратил.
can_receive_messages — можно ли пользователю отправлять сообщения. (Полезно, когда пользователь заблокировал бота, удалил чат или отправка начала падать) 
referral_code — личный реферальный код пользователя.
referred_by_user_id — ID пользователя, который пригласил этого человека.
referred_at — когда именно пользователь был привязан к рефералу.

Связи:
received_referral_bonuses — бонусы, которые этот пользователь получил как приглашенный (ReferralBonus)
earned_referral_bonuses — бонусы, которые этот пользователь заработал как реферер.
buys — покупки пользователя (Это история заказов / покупок конкретного пользователя)
deposits — пополнения пользователя (Связь с Deposit)
payments — платежные записи пользователя (Связь с Payment)
cart — корзина пользователя.
"""