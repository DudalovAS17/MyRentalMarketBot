from __future__ import annotations
from typing import Optional, List, Dict
from decimal import Decimal
from datetime import datetime

from sqlalchemy import Column, Float, DateTime, ForeignKey
from sqlalchemy import Integer, String, Text, ForeignKey, Numeric, Boolean, JSON, CheckConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.models.base import Base, TimestampMixin, ReprMixin, DictMixin

from sqlalchemy.sql import func
import time


class Item(Base, TimestampMixin, ReprMixin, DictMixin):
    """Модель предмета/вещи для аренды"""
    __tablename__ = 'items'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # владелец
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),  # удалили пользователя → снеслись его объявления
        nullable=False
    )

    # категория / подкатегория
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"),  # нельзя удалить категорию, пока есть вещи
        nullable=False
    )
    subcategory_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"),  # подкатегория может обнулиться
        nullable=True,
        index=True,
    )

    # контент
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text(), nullable=True)  # String

    # деньги
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2),
                                           nullable=False)  # стоимость аренды (за день/единицу)     # Float
    deposit: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2),
                                                       nullable=True)  # залог (может быть None)     # Float

    # место
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    coordinates: Mapped[Optional[Dict]] = mapped_column(JSON, nullable=True)  # {"lat": ..., "lng": ...}

    # статусы/флаги
    is_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_featured: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING", index=True)
    moderated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    moderated_by_admin_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    moderation_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # сроки аренды (в днях)
    min_rental_period: Mapped[int] = mapped_column(Integer, nullable=False, default=1)  # Минимальный срок аренды в днях
    max_rental_period: Mapped[Optional[int]] = mapped_column(Integer,
                                                             nullable=True)  # Максимальный срок (null - без ограничений)

    # простая аналитика
    views_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    orders_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Mixin
    # Используем time.time() вместо func.now().timestamp()
    # created_at = Column(Float, default=time.time)
    # updated_at = Column(Float, default=time.time)

    # Отношения
    owner: Mapped["User"] = relationship("User", back_populates="items", foreign_keys=[user_id])
    # category: Mapped["Category"] = relationship("Category", foreign_keys=[category_id])
    # subcategory: Mapped[Optional["Category"]] = relationship("Category", foreign_keys=[subcategory_id])
    rentals: Mapped[List["Rental"]] = relationship("Rental", back_populates="item")  # , cascade="all, delete-orphan
    item_photos: Mapped[List["Photo"]] = relationship(
        "Photo",
        back_populates="item",
        cascade="all, delete-orphan",  # удалили вещь → удалили её фото
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
        Index("ix_items_category_available", "category_id", "is_available"),
        Index("ix_items_owner_available", "user_id", "is_available"),
        Index("ix_items_created_at", "created_at"),  # поле из TimestampMixin
    )

    """
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "category_id": self.category_id,
            "subcategory_id": self.subcategory_id,
            "title": self.title,
            "description": self.description,
            "price": self.price,
            "deposit": self.deposit,
            "location": self.location,
            "coordinates": self.coordinates,
            "is_available": self.is_available,
            "is_featured": self.is_featured,
            "min_rental_period": self.min_rental_period,
            "max_rental_period": self.max_rental_period,
            "views_count": self.views_count,
            "orders_count": self.orders_count,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    """