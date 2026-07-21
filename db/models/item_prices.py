from decimal import Decimal
from typing import Optional, TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.models.base import Base


if TYPE_CHECKING:
    from db.models.item import Item

class ItemPriceTier(Base):
    """Тарифная ставка товара по длительности аренды."""

    __tablename__ = "item_price_tiers"


    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    item_id: Mapped[int] = mapped_column(
        ForeignKey("items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    min_days: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Minimum rental duration in days for this tariff.",
    )

    max_days: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Maximum rental duration in days. NULL means no upper limit.",
    )

    price_per_day: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Daily price for this rental duration tier.",
    )

    sort_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    label: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Optional display label, for example '2–7 дней'.",
    )


    # ------- Отношения | связи - -------
    item: Mapped["Item"] = relationship("Item",back_populates="price_tiers")


    __table_args__ = (
        CheckConstraint(
            "min_days >= 1",
            name="ck_item_price_tiers_min_days_positive",
        ),
        CheckConstraint(
            "max_days IS NULL OR max_days >= min_days",
            name="ck_item_price_tiers_max_days_gte_min_days",
        ),
        CheckConstraint(
            "price_per_day > 0",
            name="ck_item_price_tiers_price_positive",
        ),
    )