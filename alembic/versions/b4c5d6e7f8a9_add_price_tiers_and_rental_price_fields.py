"""add price tiers and rental price fields

Revision ID: b4c5d6e7f8a9
Revises: 7136f7e2891a
Create Date: 2026-07-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b4c5d6e7f8a9"
down_revision: Union[str, Sequence[str], None] = "7136f7e2891a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "item_price_tiers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("min_days", sa.Integer(), nullable=False, comment="Minimum rental duration in days for this tariff."),
        sa.Column("max_days", sa.Integer(), nullable=True, comment="Maximum rental duration in days. NULL means no upper limit."),
        sa.Column("price_per_day", sa.Numeric(12, 2), nullable=False, comment="Daily price for this rental duration tier."),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("label", sa.String(length=50), nullable=True, comment="Optional display label, for example '2–7 дней'."),
        sa.CheckConstraint("min_days >= 1", name="ck_item_price_tiers_min_days_positive"),
        sa.CheckConstraint("max_days IS NULL OR max_days >= min_days", name="ck_item_price_tiers_max_days_gte_min_days"),
        sa.CheckConstraint("price_per_day > 0", name="ck_item_price_tiers_price_positive"),
        sa.ForeignKeyConstraint(["item_id"], ["items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_item_price_tiers_item_id"), "item_price_tiers", ["item_id"], unique=False)

    op.add_column("rentals", sa.Column("rental_days", sa.Integer(), nullable=True))
    op.add_column("rentals", sa.Column("price_per_day_snapshot", sa.Numeric(12, 2), nullable=True))
    op.add_column("rentals", sa.Column("delivery_price", sa.Numeric(12, 2), nullable=True))
    op.create_check_constraint("ck_rentals_rental_days_positive", "rentals", "(rental_days IS NULL) OR (rental_days >= 1)")
    op.create_check_constraint("ck_rentals_price_per_day_snapshot_positive", "rentals", "(price_per_day_snapshot IS NULL) OR (price_per_day_snapshot > 0)")
    op.create_check_constraint("ck_rentals_delivery_price_non_neg", "rentals", "(delivery_price IS NULL) OR (delivery_price >= 0)")


def downgrade() -> None:
    op.drop_constraint("ck_rentals_delivery_price_non_neg", "rentals", type_="check")
    op.drop_constraint("ck_rentals_price_per_day_snapshot_positive", "rentals", type_="check")
    op.drop_constraint("ck_rentals_rental_days_positive", "rentals", type_="check")
    op.drop_column("rentals", "delivery_price")
    op.drop_column("rentals", "price_per_day_snapshot")
    op.drop_column("rentals", "rental_days")
    op.drop_index(op.f("ix_item_price_tiers_item_id"), table_name="item_price_tiers")
    op.drop_table("item_price_tiers")