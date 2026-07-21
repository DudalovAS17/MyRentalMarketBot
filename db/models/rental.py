from __future__ import annotations

from decimal import Decimal
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import Integer, String, Text, DateTime, Boolean, ForeignKey, Numeric, Enum as SAEnum, CheckConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.models.base import Base, TimestampMixin, enum_values
from status.rental_status import RentalStatus

if TYPE_CHECKING:
    from db.models.item import Item
    from db.models.review import Review
    from db.models.user import User
    from db.models.admins import Admin
    from db.models.support_ticket import SupportTicket

class Rental(Base, TimestampMixin):
    """Заявка клиента на аренду товара."""
    __tablename__ = "rentals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # id товара
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id", ondelete="RESTRICT"), nullable=False)

    # сроки аренды
    #start_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    #end_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    rental_period_text: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    rental_days: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Точное число дней, которое выставляет менеджер, чтобы подсчитать Final price.",
    )

    price_per_day_snapshot: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Цена товара за день, для конкретного промежутка дней, выбранного пользователем",
    ) # пример: если 2–7 дней → 1300 ₽ / день, то тут будет записано 1300₽

    # деньги
    total_price: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        comment="Estimated/calculated total price before final manager adjustment.",
    )
    final_price: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        comment="Final agreed price after manager adjustment.",
    )

    # статус
    status: Mapped[RentalStatus] = mapped_column(
        SAEnum(RentalStatus, name="rental_status", values_callable=enum_values),
        nullable=False,
        default=RentalStatus.REQUESTED
    )

    # сколько единиц хочет арендовать клиент
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Доставка
    delivery_needed: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    delivery_address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    delivery_price: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        comment="Точная сумма доставки, которую выставляет менеджер, чтобы подсчитать Final price.",
    )

    # клиент
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)

    # Контакты клиента из формы заявки
    client_name: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    client_phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    client_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Внутренний комментарий менеджера
    manager_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Причины финальных отрицательных решений показываются отдельно от внутреннего комментария.
    reject_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cancel_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Назначенный менеджер
    assigned_admin_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("admins.id", ondelete="SET NULL"),
        nullable=True,
    )

    in_progress_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Для аналитики («среднее время от REQUESTED до COMPLETED», «сколько заявок отменяется») нужны timestamp-ы переходов.
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


    # ------- Отношения | связи --------

    # какой товар арендуется
    item: Mapped["Item"] = relationship("Item", back_populates="rentals")

    user: Mapped["User"] = relationship("User", back_populates="rentals")

    assigned_admin: Mapped[Optional["Admin"]] = relationship(
        "Admin",
        foreign_keys=[assigned_admin_id],
        back_populates="assigned_rentals",
    )

    # какие отзывы относятся к этой заявке
    reviews: Mapped[list["Review"]] = relationship(
        "Review",
        back_populates="rental",
        cascade="all, delete-orphan",
    )

    support_tickets: Mapped[list["SupportTicket"]] = relationship("SupportTicket", back_populates="rental")

    __table_args__ = (
        # # нельзя создать аренду, которая заканчивается раньше, чем начинается
        # CheckConstraint(
        #     "(start_date IS NULL AND end_date IS NULL) OR (start_date IS NOT NULL AND end_date IS NOT NULL AND end_date > start_date)",
        #     name="ck_rentals_end_after_start",
        # ),

        # запрет отрицательной стоимости (логическая ошибка)
        CheckConstraint("(total_price IS NULL) OR (total_price >= 0)", name="ck_rentals_total_price_non_neg"),
        CheckConstraint("(final_price IS NULL) OR (final_price >= 0)", name="ck_rentals_final_price_non_neg"),
        CheckConstraint("quantity >= 1", name="ck_rentals_quantity_positive"),

        Index("ix_rentals_item_id", "item_id"),
        Index("ix_rentals_status", "status"),
        Index("ix_rentals_user_id", "user_id"),
        Index("ix_rentals_user_status", "user_id", "status"),
        Index("ix_rentals_assigned_admin_status", "assigned_admin_id", "status"),

        # получить все заявки по товару с определёнными статусами: item_id + status
        Index("ix_rentals_item_status", "item_id", "status"),
    )