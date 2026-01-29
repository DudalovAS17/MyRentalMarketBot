# db/models/user.py
from __future__ import annotations
from typing import Optional, List

from sqlalchemy import (
    Integer, String, Float, Boolean,
    CheckConstraint, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.models.base import Base, TimestampMixin, ReprMixin, DictMixin


class User(Base, TimestampMixin, ReprMixin, DictMixin):
    """Модель пользователя."""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True) # index=True

    # уникальный телеграм-id (строкой, как у тебя было)
    telegram_id: Mapped[str] = mapped_column(String(20), nullable=False, unique=True) # index=True

    # профиль
    username:   Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_name:  Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    # оставляем хранимое full_name, как в старом коде (удобно для поиска/вывода)
    full_name:  Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # рейтинг
    rating:       Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    rating_count: Mapped[int]   = mapped_column(Integer, nullable=False, default=0)

    # блокировки/флаги
    is_blocked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False) # По умолчанию пользователи не заблокированы

    # Отношения|связи
    items: Mapped[List["Item"]] = relationship(
        "Item",
        back_populates="owner",
        cascade="all, delete-orphan",   # удалили юзера → удалились его вещи (если в Item FK ondelete=CASCADE — идеально)
        single_parent=True,
        passive_deletes=True,
    ) #cascade="all, delete-orphan" → гарантирует удаление зависимостей (например, всех объявлений пользователя)

    rentals_as_owner: Mapped[List["Rental"]] = relationship(
        "Rental", foreign_keys="Rental.owner_id", back_populates="owner"
    )

    rentals_as_renter: Mapped[List["Rental"]] = relationship(
        "Rental", foreign_keys="Rental.renter_id", back_populates="renter"
    )

    # норм?
    support_tickets: Mapped[List["SupportTicket"]] = relationship(
        "SupportTicket", back_populates="user"
    )

    #reviews_given: Mapped[List["Review"]] = relationship(
    #    "Review", foreign_keys="Review.reviewer_id", back_populates="reviewer"
    #)
    #reviews_received: Mapped[List["Review"]] = relationship(
    #    "Review", foreign_keys="Review.reviewee_id", back_populates="reviewee"
    #)

    __table_args__ = (
        # валидация на уровне БД (последняя линия обороны)
        CheckConstraint("rating >= 0 AND rating <= 5", name="ck_users_rating_range"),
        CheckConstraint("rating_count >= 0",        name="ck_users_rating_count_nonneg"),
        # полезные индексы
        Index("ix_users_username", "username"),
        Index("ix_users_created_at", "created_at"),  # поле из TimestampMixin
    )

    # удобное «отображаемое имя» (не хранится в БД)
    @property
    def display_name(self) -> str:
        if self.full_name:
            return self.full_name
        if self.first_name or self.last_name:
            return f"{self.first_name or ''} {self.last_name or ''}".strip()
        return self.username or self.telegram_id
