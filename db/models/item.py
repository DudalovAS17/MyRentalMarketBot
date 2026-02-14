from __future__ import annotations

from decimal import Decimal
from datetime import datetime
from typing import Optional, List, Dict, TYPE_CHECKING
from sqlalchemy import DateTime
from sqlalchemy import Integer, String, Text, ForeignKey, Numeric, Enum as SAEnum, Boolean, JSON, CheckConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.models.base import Base, TimestampMixin
from utils.item_status import ItemStatus

if TYPE_CHECKING:
    from db.models.user import User
    from db.models.rental import Rental
    from db.models.photo import Photo

class Item(Base, TimestampMixin):
    """Модель предмета/вещи для аренды"""
    __tablename__ = 'items'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # владелец
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),  # удалил пользователя → снеслись его объявления
        nullable=False
    )

    # категория / подкатегория
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"),  # нельзя удалить категорию, пока есть вещи
        nullable=False
    )
    subcategory_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"),  # подкатегория может обнулиться
        nullable=True
    )

    # контент
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text(), nullable=True)

    # деньги
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    deposit: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)

    # место
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    coordinates: Mapped[Optional[Dict]] = mapped_column(JSON, nullable=True)  # [dict[str, Any]],   {"lat": ..., "lng": ...}

    # статусы/флаги
    is_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_featured: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    #status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    status: Mapped[ItemStatus] = mapped_column(
        SAEnum(ItemStatus, name="item_status"),
        nullable=False,
        default=ItemStatus.PENDING
    )

    # аудит админов (когда, кто, зачем)
    moderated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    #moderated_by_admin_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    moderated_by_admin_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    moderation_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # сроки аренды (в днях)
    min_rental_period: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    max_rental_period: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # простая аналитика
    views_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    orders_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Отношения
    owner: Mapped["User"] = relationship("User", back_populates="items", foreign_keys=[user_id])
    # category: Mapped["Category"] = relationship("Category", foreign_keys=[category_id])
    # subcategory: Mapped[Optional["Category"]] = relationship("Category", foreign_keys=[subcategory_id])
    rentals: Mapped[List["Rental"]] = relationship("Rental", back_populates="item")  # , cascade="all, delete-orphan
    item_photos: Mapped[List["Photo"]] = relationship(
        "Photo",
        back_populates="item",
        cascade="all, delete-orphan",  # удалил вещь → удалили её фото
        single_parent=True,
    )

    #photos = relationship("Photo", back_populates="item", cascade="all, delete-orphan")

    __table_args__ = (
        # валидации на уровне БД
        CheckConstraint("price >= 0", name="ck_item_price_nonneg"),
        CheckConstraint("(deposit IS NULL) OR (deposit >= 0)", name="ck_item_deposit_nonneg"),
        CheckConstraint("min_rental_period >= 1", name="ck_item_min_period"),
        CheckConstraint("(max_rental_period IS NULL) OR (max_rental_period >= min_rental_period)",
                        name="ck_item_max_ge_min"),
        CheckConstraint("views_count >= 0", name="ck_item_views_nonneg"),
        CheckConstraint("orders_count >= 0", name="ck_item_orders_nonneg"),

        # полезные индексы
        Index("ix_items_subcategory_id", "subcategory_id"),
        Index("ix_items_status", "status"),
        Index("ix_items_category_available", "category_id", "is_available"),
        Index("ix_items_owner_available", "user_id", "is_available"),
    )