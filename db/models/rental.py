from __future__ import annotations
from typing import Optional, List
from decimal import Decimal
from datetime import datetime
import enum

from sqlalchemy import Integer, DateTime, Boolean, ForeignKey, Numeric, Enum as SAEnum, CheckConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.models.base import Base, TimestampMixin, ReprMixin, DictMixin


class RentalStatus(enum.Enum):
    REQUESTED = "requested"      # Запрос отправлен арендатором
    CONFIRMED = "confirmed"      # Владелец подтвердил, ожидает начала аренды
    ACTIVE = "active"            # Аренда идет
    COMPLETED = "completed"      # Аренда завершена (вещь возвращена)

    REJECTED_BY_OWNER = "rejected_by_owner"    # Владелец отклонил запрос аренды
    REJECTED_BY_RENTER = "rejected_by_renter"  # Арендатор отклонил свой запрос аренды
    CANCELLED_CONFIRMED_BY_OWNER = "cancelled_confirmed_by_owner" # Владелец отменяет подтвержденную аренду
    CANCELLED_CONFIRMED_BY_RENTER = "cancelled_confirmed_by_renter" # Арендатор отменяет подтвержденную аренду
    CANCELLED_BY_OWNER = "cancelled_by_owner"  # Владелец отменяет активную аренду
    CANCELLED_BY_RENTER = "cancelled_by_renter" # Арендатор отменяет активную аренду

    DISPUTED = "disputed"        # Открыт спор


class Rental(Base, TimestampMixin, ReprMixin, DictMixin):
    """Модель аренды (сделки)"""
    __tablename__ = "rentals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)  # index=True

    # связи с вещью и пользователями
    item_id: Mapped[int] = mapped_column(
        ForeignKey("items.id", ondelete="RESTRICT"),  # не даём удалить вещь с историей аренды
        nullable=False,
        index=True
    )

    # Арендатор
    renter_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),  # не даём удалить арендатора с историями
        nullable=False,
        index=True
    )

    # Владелец
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),  # не даём удалить владельца с историями
        nullable=False,
        index=True
    )

    # сроки аренды
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_date:   Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # деньги (Decimal/Numeric — без проблем округления)
    total_price:    Mapped[Decimal]          = mapped_column(Numeric(12, 2), nullable=False)
    deposit_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)

    # статус
    status: Mapped[RentalStatus] = mapped_column(
        SAEnum(RentalStatus, name="rental_status"),
        nullable=False,
        default=RentalStatus.REQUESTED,
        index=True,
    )

    # потом заменятся через Alembic?
    owner_handover_confirmed: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    renter_receive_confirmed: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    # ORM-связи
    item:   Mapped["Item"] = relationship("Item", back_populates="rentals")
    renter: Mapped["User"] = relationship("User", foreign_keys=[renter_id], back_populates="rentals_as_renter")
    owner:  Mapped["User"] = relationship("User", foreign_keys=[owner_id],  back_populates="rentals_as_owner")
    reviews: Mapped[List["Review"]] = relationship(
        "Review",
        back_populates="rental",
        cascade="all, delete-orphan", # удалил сделку → удалились все отзывы
        #lazy="selectin",
    )

    __table_args__ = (
        # Валидации на уровне БД (защита от некорректных данных ещё до того, как они попадут в таблицу)

        # нельзя создать аренду, которая заканчивается раньше, чем начинается
        CheckConstraint("end_date > start_date", name="ck_rentals_end_after_start"),

        # запрет отрицательной стоимости (логическая ошибка)
        CheckConstraint("total_price >= 0", name="ck_rentals_total_price_nonneg"),

        # депозит тоже не может быть отрицательным
        CheckConstraint("(deposit_amount IS NULL) OR (deposit_amount >= 0)", name="ck_rentals_deposit_nonneg"),


        # получить все сделки по вещи с определёнными статусами: item_id + status
        Index("ix_rentals_item_status", "item_id", "status"),

        # история арендатора (история бронирований): renter_id + status
        Index("ix_rentals_renter_status", "renter_id", "status"),

        # история арендодателя (его подтверждения): owner_id + status
        Index("ix_rentals_owner_status", "owner_id", "status"),

        # Index("ix_rentals_created_at", "created_at"),  # из TimestampMixin
    )


"""
Здесь были: 

def __repr__(self) - спользуется для логов, отладочных сообщений, консоли разработчика -> logger.info(rental)

def to_dict(self) - Превращает ORM-объект SQLAlchemy (Rental) → обычный Python-словарь (приводит их к JSON-friendly виду)
    # Тут status, даты, деньги, остальные — обычные питоновские типы
    
    FOR "status":
        Enum -> str ()
    
    FOR "start_date", "end_date", "created_at", "updated_at":
        datetime -> ISO
    
    FOR "total_price", "deposit_amount":
        Decimal -> str (или float)

    Возвращаем словарь уже в «JSON-дружелюбном» виде: строки вместо Enum и дат
    


Правильный проф-подход:
    сериализация → в Pydantic (RentalOut)
    форматирование/JSON → в helpers/formatters
"""