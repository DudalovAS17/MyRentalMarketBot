"""set server defaults for timestamps

Revision ID: 5c09cf4d1509
Revises: c0dab82dbe62
Create Date: 2026-03-14 14:41:37.354648

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5c09cf4d1509'
down_revision: Union[str, Sequence[str], None] = 'c0dab82dbe62'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLES_WITH_TIMESTAMPS = [
    "categories",
    "users",
    "items",
    "rentals",
    "reviews",
    "photos",
    "support_tickets",
    "admin_actions",
]

def upgrade() -> None:
    for table_name in TABLES_WITH_TIMESTAMPS:
        op.alter_column(
            table_name,
            "created_at",
            existing_type=sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            existing_nullable=False,
        )
        op.alter_column(
            table_name,
            "updated_at",
            existing_type=sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            existing_nullable=False,
        )


def downgrade() -> None:
    for table_name in TABLES_WITH_TIMESTAMPS:
        op.alter_column(
            table_name,
            "created_at",
            existing_type=sa.DateTime(timezone=True),
            server_default=None,
            existing_nullable=False,
        )
        op.alter_column(
            table_name,
            "updated_at",
            existing_type=sa.DateTime(timezone=True),
            server_default=None,
            existing_nullable=False,
        )