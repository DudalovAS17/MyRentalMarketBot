from __future__ import annotations

from decimal import Decimal
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import DateTime
from sqlalchemy import Integer, String, Text, ForeignKey, Numeric, Enum as SAEnum, Boolean, CheckConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.models.base import Base, TimestampMixin
from status.item_status import ItemStatus

if TYPE_CHECKING:
    from db.models.category import Category
    from db.models.admins import Admin
    from db.models.rental import Rental
    from db.models.photo import Photo
    from db.models.item_characteristics import ItemCharacteristic
    from db.models.review import Review
    from db.models.support_ticket import SupportTicket


class Item(Base, TimestampMixin):
    """Товар каталога компании для аренды."""
    __tablename__ = 'items'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # категория / подкатегория
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False
    )
    subcategory_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True
    )

    # контент
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    short_description: Mapped[Optional[str]] = mapped_column(String(300), nullable=True) # NEW

    # деньги
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False) # price_per_day
    price_text: Mapped[Optional[str]] = mapped_column(String(100), nullable=True) # NEW

    # Количество в наличии
    available_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1) # NEW

    # Рекомендуемый товар?
    is_featured: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # нужно, чтобы товары в подкатегории шли в нужном порядке
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Enum ItemStatus — модерация/публикация
    status: Mapped[ItemStatus] = mapped_column(
        SAEnum(ItemStatus, name="item_status"),
        nullable=False,
        default=ItemStatus.PENDING # теперь правильнее ItemStatus.DRAFT
    )

    created_by_admin_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("admins.id", ondelete="SET NULL"),
        nullable=True,
    )

    updated_by_admin_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("admins.id", ondelete="SET NULL"),
        nullable=True,
    )

    moderated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True) # updated_at

    # сроки аренды (в днях)
    min_rental_period: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    max_rental_period: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # простая аналитика: Количество просмотров - Количество заявок
    views_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    orders_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


    # ------- Отношения | связи --------

    category: Mapped["Category"] = relationship("Category", foreign_keys=[category_id])
    subcategory: Mapped[Optional["Category"]] = relationship("Category", foreign_keys=[subcategory_id])
    rentals: Mapped[list["Rental"]] = relationship("Rental", back_populates="item")
    item_photos: Mapped[list["Photo"]] = relationship(
        "Photo",
        back_populates="item",
        cascade="all, delete-orphan",
        single_parent=True
    )

    characteristics: Mapped[list["ItemCharacteristic"]] = relationship(
        "ItemCharacteristic",
        back_populates="item",
        cascade="all, delete-orphan",
        single_parent=True,
    )

    created_by_admin: Mapped[Optional["Admin"]] = relationship(
        "Admin",
        foreign_keys=[created_by_admin_id],
        back_populates="created_items",
    )

    updated_by_admin: Mapped[Optional["Admin"]] = relationship(
        "Admin",
        foreign_keys=[updated_by_admin_id],
        back_populates="updated_items",
    )

    reviews: Mapped[list["Review"]] = relationship("Review", back_populates="item")
    support_tickets: Mapped[list["SupportTicket"]] = relationship("SupportTicket", back_populates="item")

    __table_args__ = (
        CheckConstraint("(price IS NULL) OR (price >= 0)", name="ck_items_price_non_neg"), # price_per_day
        CheckConstraint("min_rental_period >= 1", name="ck_items_min_period"),
        CheckConstraint("(max_rental_period IS NULL) OR (max_rental_period >= min_rental_period)",
                        name="ck_items_max_ge_min"),

        CheckConstraint("sort_order >= 0", name="ck_items_sort_order_non_neg"),
        CheckConstraint("available_quantity >= 0", name="ck_items_available_quantity_non_neg"),
        CheckConstraint("views_count >= 0", name="ck_items_views_non_neg"),
        CheckConstraint("orders_count >= 0", name="ck_items_orders_non_neg"),

        Index("ix_items_category_id", "category_id"),
        Index("ix_items_subcategory_id", "subcategory_id"),
        Index("ix_items_status", "status"),
        Index("ix_items_category_status", "category_id", "status"),
        Index("ix_items_subcategory_status", "subcategory_id", "status"),
        Index("ix_items_featured", "is_featured"),
        Index("ix_items_sort_order", "sort_order"),
        Index("ix_items_subcategory_status_sort", "subcategory_id", "status", "sort_order"),
    )


""" Дополнительные будущие поля:
item_type — тип товара.
private_data — скрытые данные товара.
is_new — новый ли товар. """