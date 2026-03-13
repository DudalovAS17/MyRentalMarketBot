from __future__ import annotations

from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import Integer, String, Float, Boolean, CheckConstraint, Enum as SAEnum, Index, DateTime, Text, ForeignKey, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.models.base import Base, TimestampMixin
from utils.user_status import AccountStatus

if TYPE_CHECKING:
    from db.models.item import Item
    from db.models.rental import Rental
    from db.models.support_ticket import SupportTicket
    #from db.models.review import Review

class User(Base, TimestampMixin):
    """Модель пользователя."""
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

    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # В идеале is_admin должен вычисляться через settings.admin_ids на уровне middleware/сервисов
    # и не храниться в БД (иначе рассинхрон). Но оставляем как “наследие” до отдельной миграции.
    # ALTER TABLE users DROP COLUMN IF EXISTS is_admin; - сделай, когда будешь убирать

    # рейтинг
    rating: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    rating_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # блокировки/флаги (старый, мы его пока не трогаем, чтобы не ломать проект)
    is_blocked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # новый “правильный” флаг
    account_status: Mapped[AccountStatus] = mapped_column(
        SAEnum(AccountStatus, name="account_status"),
        nullable=False,
        default=AccountStatus.ACTIVE
    )

    # аудит админов (когда, кто, зачем)
    banned_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    banned_by_admin_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True) # было Integer
    ban_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Отношения|связи
    items: Mapped[list["Item"]] = relationship(
        "Item",
        back_populates="owner",
        foreign_keys="Item.user_id",
        cascade="all, delete-orphan",   # удалили юзера → удалились его вещи (если в Item FK ondelete=CASCADE — идеально)
        single_parent=True,
        passive_deletes=True,
    ) #cascade="all, delete-orphan" → гарантирует удаление зависимостей (например, всех объявлений пользователя)

    rentals_as_owner: Mapped[list["Rental"]] = relationship(
        "Rental", foreign_keys="Rental.owner_id", back_populates="owner"
    )

    rentals_as_renter: Mapped[list["Rental"]] = relationship(
        "Rental", foreign_keys="Rental.renter_id", back_populates="renter"
    )

    support_tickets: Mapped[list["SupportTicket"]] = relationship(
        "SupportTicket", back_populates="user"
    )

    #reviews_given: Mapped[list["Review"]] = relationship(
    #    "Review", foreign_keys="Review.reviewer_id", back_populates="reviewer"
    #)
    #reviews_received: Mapped[list["Review"]] = relationship(
    #    "Review", foreign_keys="Review.reviewee_id", back_populates="reviewee"
    #)

    __table_args__ = (
        # валидация на уровне БД (последняя линия обороны)
        CheckConstraint("rating >= 0 AND rating <= 5", name="ck_users_rating_range"),
        CheckConstraint("rating_count >= 0", name="ck_users_rating_count_non_neg"),

        # полезные индексы
        Index("ix_users_account_status", "account_status"),
        Index("ix_users_username", "username"),
    )


""" Дополнительные будущие поля:
top_up_amount — сколько всего денег пользователь пополнил.
consume_records — сколько всего денег пользователь потратил.
can_receive_messages — можно ли пользователю отправлять сообщения. (Полезно, когда пользователь заблокировал бота, удалил чат или отправка начала падать) 
language — язык пользователя.
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