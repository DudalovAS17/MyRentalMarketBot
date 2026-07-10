"""add rental decision reasons

Revision ID: c3d4e5f6a7b8
Revises: 9f7b3a2c1d4e
Create Date: 2026-07-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "9f7b3a2c1d4e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("rentals", sa.Column("reject_reason", sa.Text(), nullable=True))
    op.add_column("rentals", sa.Column("cancel_reason", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("rentals", "cancel_reason")
    op.drop_column("rentals", "reject_reason")