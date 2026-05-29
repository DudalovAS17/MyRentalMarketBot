from __future__ import annotations

from typing import TYPE_CHECKING
from sqlalchemy import CheckConstraint, UniqueConstraint, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from db.models.item import Item


class ItemCharacteristic(Base, TimestampMixin):
    """Характеристика товара каталога.

    Используется для отображения технических параметров товара
    в карточке: вес, мощность, габариты, глубина уплотнения и т.д."""

    __tablename__ = "item_characteristics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    item_id: Mapped[int] = mapped_column(ForeignKey("items.id", ondelete="CASCADE"), nullable=False)

    name: Mapped[str] = mapped_column(String(100), nullable=False)

    value: Mapped[str] = mapped_column(String(200), nullable=False)

    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


    # ------- Отношения | связи --------

    item: Mapped["Item"] = relationship("Item", back_populates="characteristics")

    __table_args__ = (
        CheckConstraint("sort_order >= 0", name="ck_item_characteristics_sort_order_non_neg"),

        UniqueConstraint("item_id", "name", name="uq_item_characteristics_item_id_name"),

        Index("ix_item_characteristics_item_id", "item_id"),
        Index("ix_item_characteristics_item_sort_order", "item_id", "sort_order"),
    )