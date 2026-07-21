"""add support messages

Revision ID: 9f7b3a2c1d4e
Revises: 2ae09c5a716a
Create Date: 2026-07-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9f7b3a2c1d4e"
down_revision: Union[str, Sequence[str], None] = "2ae09c5a716a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "support_messages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ticket_id", sa.Integer(), nullable=False),
        sa.Column("sender_type", sa.Enum("user", "admin", "system", name="support_message_sender_type"), nullable=False),
        sa.Column("sender_user_id", sa.Integer(), nullable=True),
        sa.Column("sender_admin_id", sa.Integer(), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "(sender_type = 'user' AND sender_user_id IS NOT NULL AND sender_admin_id IS NULL) "
            "OR (sender_type = 'admin' AND sender_admin_id IS NOT NULL AND sender_user_id IS NULL) "
            "OR (sender_type = 'system')",
            name=op.f("ck_support_messages_ck_support_messages_sender_consistent"),
        ),
        sa.ForeignKeyConstraint(["sender_admin_id"], ["admins.id"], name=op.f("fk_support_messages_sender_admin_id_admins"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["sender_user_id"], ["users.id"], name=op.f("fk_support_messages_sender_user_id_users"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["ticket_id"], ["support_tickets.id"], name=op.f("fk_support_messages_ticket_id_support_tickets"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_support_messages")),
    )
    op.create_index("ix_support_messages_sender_admin_id", "support_messages", ["sender_admin_id"], unique=False)
    op.create_index("ix_support_messages_sender_user_id", "support_messages", ["sender_user_id"], unique=False)
    op.create_index("ix_support_messages_ticket_created", "support_messages", ["ticket_id", "created_at"], unique=False)

    op.execute(
        """
        INSERT INTO support_messages (ticket_id, sender_type, sender_user_id, text, created_at, updated_at)
        SELECT id, 'user', user_id, text, created_at, updated_at
        FROM support_tickets
        """
    )


def downgrade() -> None:
    op.drop_index("ix_support_messages_ticket_created", table_name="support_messages")
    op.drop_index("ix_support_messages_sender_user_id", table_name="support_messages")
    op.drop_index("ix_support_messages_sender_admin_id", table_name="support_messages")
    op.drop_table("support_messages")
    sa.Enum("user", "admin", "system", name="support_message_sender_type").drop(op.get_bind(), checkfirst=True)
