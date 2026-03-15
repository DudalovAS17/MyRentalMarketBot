"""delete is_blocked, is_admin, and rating to Decimal

Revision ID: ff171c9e67ce
Revises: 5c09cf4d1509
Create Date: 2026-03-14 15:08:26.730396

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ff171c9e67ce'
down_revision: Union[str, Sequence[str], None] = '5c09cf4d1509'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("users", "is_blocked")
    op.drop_column("users", "is_admin")

    op.alter_column(
        "users",
        "rating",
        existing_type=sa.Float(),
        type_=sa.Numeric(3, 2),
        existing_nullable=False,
        existing_server_default=None,
    )


def downgrade() -> None:
    op.alter_column(
        "users",
        "rating",
        existing_type=sa.Numeric(3, 2),
        type_=sa.Float(),
        existing_nullable=False,
        existing_server_default=None,
    )

    op.add_column(
        "users",
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "users",
        sa.Column("is_blocked", sa.Boolean(), nullable=False, server_default=sa.false()),
    )