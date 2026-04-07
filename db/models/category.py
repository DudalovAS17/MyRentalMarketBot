from __future__ import annotations

from typing import Optional
from sqlalchemy import Integer, String, ForeignKey, Index, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.models.base import Base , TimestampMixin


class Category(Base, TimestampMixin):
    """ Единая таблица для категорий и подкатегорий. Подкатегория — это Category с parent_id = id родителя"""
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    emoji: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    parent_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=True,
    )

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
        CheckConstraint("parent_id IS NULL OR parent_id <> id", name="ck_categories_no_self_parent"),
        Index("ix_categories_parent_id", "parent_id"),
    )