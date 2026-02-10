from __future__ import annotations
from typing import Optional, List

from sqlalchemy import Integer, String, ForeignKey, Index, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.models.base import Base , TimestampMixin #, ReprMixin, DictMixin

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

    # Отношения
    parent: Mapped[Optional["Category"]] = relationship(
        "Category",
        remote_side=[id],
        back_populates="subcategories",
    )
    subcategories: Mapped[List["Category"]] = relationship( # list["Category"]
        "Category",
        back_populates="parent",
        cascade="all, delete-orphan",
        single_parent=True, # важно для delete-orphan в self-referential
        passive_deletes=True, # уважаем ondelete на стороне БД
    )

    __table_args__ = (
        # в рамках одного родителя имя уникально
        UniqueConstraint("parent_id", "name"),

        # защита от «сам себе родитель»
        CheckConstraint("parent_id IS NULL OR parent_id <> id", name="no_self_parent"),

        # для быстрого получения категорий по parent_id
        Index("ix_categories_parent_id", "parent_id"),
    )

    # __repr__(self)
    # to_dict(self)
