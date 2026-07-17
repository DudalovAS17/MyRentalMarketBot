"""drop rental start and end dates

Revision ID: f89e6eff0ea7
Revises: c3d4e5f6a7b8
Create Date: 2026-07-18 00:30:17.375908

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f89e6eff0ea7'
down_revision: Union[str, Sequence[str], None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("rentals", "start_date")
    op.drop_column("rentals", "end_date")


def downgrade() -> None:
    op.add_column(
        "rentals",
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "rentals",
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=True),
    )