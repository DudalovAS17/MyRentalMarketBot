from __future__ import annotations

from decimal import Decimal
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import Integer, DateTime, Boolean, ForeignKey, Numeric, Enum as SAEnum, CheckConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.models.base import Base, TimestampMixin
from status.rental_status import RentalStatus

if TYPE_CHECKING:
    from db.models.item import Item
    from db.models.review import Review
    from db.models.user import User

class Rental(Base, TimestampMixin):
    """Модель аренды (сделки)"""
    __tablename__ = "rentals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # связи с вещью и пользователями
    item_id: Mapped[int] = mapped_column(
        ForeignKey("items.id", ondelete="RESTRICT"),
        nullable=False
    )

    # Арендатор
    renter_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False
    )

    # Владелец
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False
    )

    # сроки аренды
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # деньги
    total_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    deposit_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)

    # статус
    status: Mapped[RentalStatus] = mapped_column(
        SAEnum(RentalStatus, name="rental_status"),
        nullable=False,
        default=RentalStatus.REQUESTED
    )

    # потом заменятся через Alembic?
    owner_handover_confirmed: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    renter_receive_confirmed: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    # Для аналитики («среднее время от REQUESTED до COMPLETED», «сколько сделок отменяется») нужны timestamp-ы переходов.
    # cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    # completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # ------- Отношения | связи --------

    # какая вещь арендуется
    item: Mapped["Item"] = relationship("Item", back_populates="rentals")

    # кто арендатор | кто владелец
    renter: Mapped["User"] = relationship("User", foreign_keys=[renter_id], back_populates="rentals_as_renter")
    owner: Mapped["User"] = relationship("User", foreign_keys=[owner_id],  back_populates="rentals_as_owner")

    # какие отзывы относятся к этой сделке
    reviews: Mapped[list["Review"]] = relationship(
        "Review",
        back_populates="rental",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        # нельзя создать аренду, которая заканчивается раньше, чем начинается
        CheckConstraint("end_date > start_date", name="ck_rentals_end_after_start"),

        # запрет отрицательной стоимости (логическая ошибка)
        CheckConstraint("total_price >= 0", name="ck_rentals_total_price_non_neg"),

        # депозит тоже не может быть отрицательным
        CheckConstraint("(deposit_amount IS NULL) OR (deposit_amount >= 0)", name="ck_rentals_deposit_non_neg"),

        Index("ix_rentals_item_id", "item_id"),
        Index("ix_rentals_renter_id", "renter_id"),
        Index("ix_rentals_owner_id", "owner_id"),
        Index("ix_rentals_status", "status"),

        # получить все сделки по вещи с определёнными статусами: item_id + status
        Index("ix_rentals_item_status", "item_id", "status"),

        # история арендатора (история бронирований): renter_id + status
        Index("ix_rentals_renter_status", "renter_id", "status"),

        # история арендодателя (его подтверждения): owner_id + status
        Index("ix_rentals_owner_status", "owner_id", "status"),

        # Index("ix_rentals_created_at", "created_at"),  # из TimestampMixin
    )