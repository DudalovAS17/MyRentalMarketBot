# Template: ORM Model

ORM-модель описывает таблицу, связи и DB-level ограничения. Бизнес-логика — не здесь.

Правила:
- Используем SQLAlchemy 2 style: `Mapped[...] = mapped_column(...)`.
- Наследуемся от `Base`; для стандартных дат — `TimestampMixin`.
- Для связей с type hints используем `TYPE_CHECKING`, чтобы не ловить циклические импорты.
- Enum в БД задаём через `SAEnum(..., name="...")`.
- Nullable поля явно помечаем `Optional[...]` и `nullable=True`.
- Внешние ключи получают понятный `ondelete` (`RESTRICT`, `SET NULL`, `CASCADE`).
- Индексы и `CheckConstraint` кладём в `__table_args__`.

---

### Каноничный шаблон

```python
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional, TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.models.base import Base, TimestampMixin
from status.item_status import ItemStatus

if TYPE_CHECKING:
    from db.models.admins import Admin
    from db.models.category import Category
    from db.models.rental import Rental


class Item(Base, TimestampMixin):
    """Товар каталога компании для аренды."""

    __tablename__ = "items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False,
    )
    subcategory_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
    )

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    short_description: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)

    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    price_text: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    available_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_featured: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    status: Mapped[ItemStatus] = mapped_column(
        SAEnum(ItemStatus, name="item_status"),
        nullable=False,
        default=ItemStatus.DRAFT,
    )

    created_by_admin_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("admins.id", ondelete="SET NULL"),
        nullable=True,
    )
    updated_by_admin_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("admins.id", ondelete="SET NULL"),
        nullable=True,
    )
    moderated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    min_rental_period: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    max_rental_period: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    views_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    orders_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # ------- relationships --------
    category: Mapped["Category"] = relationship("Category", foreign_keys=[category_id])
    subcategory: Mapped[Optional["Category"]] = relationship("Category", foreign_keys=[subcategory_id])
    rentals: Mapped[list["Rental"]] = relationship("Rental", back_populates="item")

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

    __table_args__ = (
        CheckConstraint("price >= 0", name="ck_items_price_non_neg"),
        CheckConstraint("min_rental_period >= 1", name="ck_items_min_period"),
        CheckConstraint(
            "(max_rental_period IS NULL) OR (max_rental_period >= min_rental_period)",
            name="ck_items_max_ge_min",
        ),
        CheckConstraint("available_quantity >= 0", name="ck_items_available_quantity_non_neg"),
        Index("ix_items_category_id", "category_id"),
        Index("ix_items_subcategory_id", "subcategory_id"),
        Index("ix_items_status", "status"),
        Index("ix_items_category_status", "category_id", "status"),
    )
```

---

### Checklist
- [ ] `__tablename__` во множественном числе и совпадает с миграциями.
- [ ] Все nullable поля имеют `Optional[...]` и `nullable=True`.
- [ ] Для денежных значений используется `Decimal` + `Numeric`, не `float`.
- [ ] Для счетчиков/количеств есть `CheckConstraint >= 0`.
- [ ] Частые фильтры имеют индексы.
- [ ] Связи используют `back_populates`, если обратная сторона есть в модели.