# db/models/rental.py
from __future__ import annotations
from typing import Optional, List, Any
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
    """Модель аренды (сделки)

    Связи:
    item_id  → Item
    renter_id → User (арендатор)
    owner_id  → User (владелец вещи)
    """
    __tablename__ = "rentals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)  # index=True

    # связи с вещью и пользователями
    item_id: Mapped[int] = mapped_column(
        ForeignKey("items.id", ondelete="RESTRICT"),  # не даём удалить вещь с историей аренды
        nullable=False,
        index=True
    )

    renter_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),  # не даём удалить арендатора с историями
        nullable=False,
        index=True
    ) # Тот, кто арендует

    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),  # не даём удалить владельца с историями
        nullable=False,
        index=True
    ) # Тот, кто сдает (владелец item)

    # сроки аренды
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_date:   Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # деньги (Decimal/Numeric — без проблем округления)
    total_price:    Mapped[Decimal]          = mapped_column(Numeric(12, 2), nullable=False) # Общая стоимость аренды за период
    deposit_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True) # Сумма залога, если был

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
        cascade="all, delete-orphan", # удалили сделку → удалились все отзывы
        #lazy="selectin",
    )

    __table_args__ = (
        # Валидации на уровне БД (защита от некорректных данных ещё до того, как они попадут в таблицу)
        CheckConstraint("end_date > start_date", name="ck_rentals_end_after_start"), # нельзя создать аренду, которая заканчивается раньше, чем начинается
        CheckConstraint("total_price >= 0", name="ck_rentals_total_price_nonneg"), # запрет отрицательной стоимости (логическая ошибка)
        CheckConstraint("(deposit_amount IS NULL) OR (deposit_amount >= 0)", name="ck_rentals_deposit_nonneg"), # депозит тоже не может быть отрицательным
        # Индексы под реальные выборки
        Index("ix_rentals_item_status", "item_id", "status"), # получить все сделки по вещи с определёнными статусами: item_id + status
        Index("ix_rentals_renter_status", "renter_id", "status"), # история арендатора (история бронирований): renter_id + status
        Index("ix_rentals_owner_status", "owner_id", "status"), # история арендодателя (его подтверждения): owner_id + status
        #Index("ix_rentals_created_at", "created_at"),  # из TimestampMixin
    )

    # Используется для логов, отладочных сообщений, консоли разработчика -> logger.info(rental)
    def __repr__(self) -> str:
        return (
            f"<Rental id={self.id} item_id={self.item_id} "
            f"renter_id={self.renter_id} owner_id={self.owner_id} "
            f"status={getattr(self.status, 'value', self.status)}>"
        ) # <Rental id=7 item_id=33 renter_id=10 owner_id=4 status=requested>

    # Превращает SQLAlchemy-модель → обычный Python-словарь (приводит их к JSON-friendly виду)
    def to_dict(self) -> dict[str, Any]:
        """Тут status, даты, деньги,
        остальные — обычные питоновские типы"""
        d = DictMixin.to_dict(self)

        # Enum -> str
        d["status"] = self.status.value if isinstance(self.status, enum.Enum) else self.status
        # status — это Enum (RentalStatus.REQUESTED и т. п.)

        # datetime -> ISO
        for k in ("start_date", "end_date", "created_at", "updated_at"):
            if isinstance(d.get(k), datetime):
                d[k] = d[k].isoformat()
        # даты (start_date, end_date, created_at, updated_at) — это datetime

        # Decimal -> str (или float)
        for m in ("total_price", "deposit_amount"):
            if isinstance(d.get(m), Decimal):
                d[m] = str(d[m])
        # деньги (total_price, deposit_amount) — это Decimal

        return d # Возвращаем словарь уже в «JSON-дружелюбном» виде: строки вместо Enum и дат
    """ Инфа
    SQLAlchemy-модель содержит данные, которые нельзя сохранить в JSON:
    -Enum
    -datetime
    -Decimal
    
    Без преобразования:
    json.dumps(rental) → выдаст ошибку.
    """


"""
Правильный проф-подход:
    сериализация → в Pydantic (RentalOut)
    форматирование/JSON → в helpers/formatters

Что сделать быстро: ripgrep по проекту:
    to_dict(
    repr( (если где-то полагались на кастомный repr)
"""