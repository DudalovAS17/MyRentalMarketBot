"""rename admin_id to admin_tg_id

Revision ID: 6788a9394101
Revises: ff171c9e67ce
Create Date: 2026-03-29 17:45:25.823892

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6788a9394101'
down_revision: Union[str, Sequence[str], None] = 'ff171c9e67ce'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("admin_actions", "admin_id", new_column_name="admin_tg_id")
    op.drop_index("ix_admin_actions_admin_id", table_name="admin_actions")
    op.create_index("ix_admin_actions_admin_tg_id", "admin_actions", ["admin_tg_id"], unique=False)

def downgrade() -> None:
    op.drop_index("ix_admin_actions_admin_tg_id", table_name="admin_actions")
    op.create_index("ix_admin_actions_admin_id", "admin_actions", ["admin_id"], unique=False)
    op.alter_column("admin_actions", "admin_tg_id", new_column_name="admin_id")
