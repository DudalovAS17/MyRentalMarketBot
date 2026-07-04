# AGENT: Models

Файл задаёт правила для слоя `db/models/` в `MyRentalMarketBot`.

Нужен агентам, которые:
- анализируют SQLAlchemy ORM-модели;
- добавляют или правят модели;
- ревьюят FK, constraints, indexes, relationships и delete semantics.

Главный принцип:

> ORM-модель описывает **структуру хранения**, но не содержит **бизнес-сценарии**, **UI** и **DTO-сериализацию**.

---

## 1) Scope слоя

`db/models/` — SQLAlchemy ORM persistence structure.

Разрешено:
- `Base`, `TimestampMixin`;
- SQLAlchemy 2 style `Mapped[...]`, `mapped_column(...)`, `relationship(...)`;
- `ForeignKey`, `CheckConstraint`, `UniqueConstraint`, `Index`;
- `SAEnum(EnumClass, name="...")`;
- `DateTime(timezone=True)`, `Numeric`, `BigInteger`, `Text`, `String`, `Boolean`;
- `TYPE_CHECKING` imports для type hints relationships.

Запрещено:
- Telegram/FSM/UI зависимости;
- service/business logic;
- статусные переходы и policy checks;
- `to_dict()` / JSON/UI serialization как канон;
- форматирование данных для пользователя;
- создание Pydantic DTO внутри модели.

---

## 2) Каноны полей

Primary key:
- `id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)`.

Foreign key:
- всегда явный `ForeignKey("table.id", ondelete="...")`;
- `RESTRICT`, если нельзя удалить связанную запись с историей;
- `SET NULL`, если связь audit/optional и запись должна жить дальше;
- `CASCADE` только когда дочерняя запись не имеет смысла без родителя.

Nullable:
- `Optional[...]` должен совпадать с `nullable=True`;
- не смешивать `Optional` и `nullable=False`.

Money:
- `Decimal` + `Numeric(precision, scale)`;
- не использовать `float`.

Telegram IDs:
- хранить через `BigInteger`;
- называть `telegram_id`, `admin_tg_id`, `*_tg_id`, чтобы не путать с DB FK.

Datetime:
- только `DateTime(timezone=True)`;
- aware UTC;
- не использовать naive `datetime.now()` / `datetime.utcnow()`.

---

## 3) Пример модели

```python
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional, TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, DateTime, Enum as SAEnum, ForeignKey, Index, Integer, Numeric, String, Text
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

    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False)
    subcategory_id: Mapped[Optional[int]] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)

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

    created_by_admin_id: Mapped[Optional[int]] = mapped_column(ForeignKey("admins.id", ondelete="SET NULL"), nullable=True)
    updated_by_admin_id: Mapped[Optional[int]] = mapped_column(ForeignKey("admins.id", ondelete="SET NULL"), nullable=True)
    moderated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    min_rental_period: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    max_rental_period: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    views_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    orders_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    category: Mapped["Category"] = relationship("Category", foreign_keys=[category_id])
    subcategory: Mapped[Optional["Category"]] = relationship("Category", foreign_keys=[subcategory_id])
    rentals: Mapped[list["Rental"]] = relationship("Rental", back_populates="item")
    created_by_admin: Mapped[Optional["Admin"]] = relationship("Admin", foreign_keys=[created_by_admin_id])
    updated_by_admin: Mapped[Optional["Admin"]] = relationship("Admin", foreign_keys=[updated_by_admin_id])

    __table_args__ = (
        CheckConstraint("price >= 0", name="ck_items_price_non_neg"),
        CheckConstraint("min_rental_period >= 1", name="ck_items_min_period"),
        CheckConstraint("(max_rental_period IS NULL) OR (max_rental_period >= min_rental_period)", name="ck_items_max_ge_min"),
        CheckConstraint("available_quantity >= 0", name="ck_items_available_quantity_non_neg"),
        Index("ix_items_category_id", "category_id"),
        Index("ix_items_subcategory_id", "subcategory_id"),
        Index("ix_items_status", "status"),
        Index("ix_items_category_status", "category_id", "status"),
    )
```

---

## 4) Relationships

Relationship должен отражать реальную ownership/delete семантику.

Используем:
- type hints `Mapped[...]`;
- `back_populates`, если обратная сторона есть;
- `cascade="all, delete-orphan"` только для owned child rows;
- `single_parent=True`, если child не может принадлежать двум родителям.

Не добавляем relationship “на всякий случай”, если repo/read-case его не использует.

---

## 5) Constraints и indexes

Constraints:
- money/count fields: `>= 0`;
- min/max periods: `max IS NULL OR max >= min`;
- enum/status consistency — через enum + service transitions.

Indexes:
- FK поля;
- status поля;
- частые пары фильтрации (`category_id + status`, `subcategory_id + status`);
- сортировочные поля, если они реально используются в каталоге.

---

## 6) Checklist

- [ ] Модель наследуется от `Base`, а timestamp-доменные сущности — от `TimestampMixin`.
- [ ] Nullable typing совпадает с `nullable`.
- [ ] FK имеет явный `ondelete`.
- [ ] Деньги — `Decimal` + `Numeric`.
- [ ] Telegram ID — `BigInteger` и явно назван как Telegram ID.
- [ ] Есть constraints для числовых инвариантов хранения.
- [ ] Есть indexes для частых фильтров.
- [ ] Нет DTO/UI/service/business logic в модели.