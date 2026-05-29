from __future__ import annotations

from typing import Optional
from sqlalchemy import Integer, String, Boolean, ForeignKey, Index, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.models.base import Base , TimestampMixin


class Category(Base, TimestampMixin):
    """Категории и подкатегории каталога товаров компании."""
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    emoji: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    parent_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=True,
    )

    # порядок отображения
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # показывать/скрывать категорию
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # машинное имя для callback/deeplink/seed-данных
    slug: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)


    # ------- Отношения | связи - -------

    parent: Mapped[Optional["Category"]] = relationship(
        "Category",
        remote_side="Category.id",
        back_populates="subcategories",
    )
    subcategories: Mapped[list["Category"]] = relationship(
        "Category",
        back_populates="parent",
        cascade="all, delete-orphan",
        single_parent=True,
        passive_deletes=True,
    )

    __table_args__ = (
        UniqueConstraint("parent_id", "name", name="uq_categories_parent_id_name"),
        UniqueConstraint("parent_id", "slug", name="uq_categories_parent_id_slug"),

        CheckConstraint("parent_id IS NULL OR parent_id <> id", name="ck_categories_no_self_parent"),
        CheckConstraint("sort_order >= 0", name="ck_categories_sort_order_non_neg"),

        Index("ix_categories_parent_id", "parent_id"),
        Index("ix_categories_parent_active", "parent_id", "is_active"),
        Index("ix_categories_sort_order", "sort_order"),
    )