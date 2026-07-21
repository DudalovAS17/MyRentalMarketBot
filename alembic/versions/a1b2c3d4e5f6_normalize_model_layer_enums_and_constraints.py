"""normalize model layer enums and constraints

Revision ID: a1b2c3d4e5f6
Revises: f89e6eff0ea7
Create Date: 2026-07-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "f89e6eff0ea7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _rename_enum_value(enum_name: str, old_value: str, new_value: str) -> None:
    op.execute(
        sa.text(
            f"""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1
                    FROM pg_enum e
                    JOIN pg_type t ON t.oid = e.enumtypid
                    WHERE t.typname = '{enum_name}' AND e.enumlabel = '{old_value}'
                ) AND NOT EXISTS (
                    SELECT 1
                    FROM pg_enum e
                    JOIN pg_type t ON t.oid = e.enumtypid
                    WHERE t.typname = '{enum_name}' AND e.enumlabel = '{new_value}'
                ) THEN
                    ALTER TYPE {enum_name} RENAME VALUE '{old_value}' TO '{new_value}';
                END IF;
            END $$;
            """
        )
    )


def upgrade() -> None:
    op.drop_constraint(
        op.f("fk_categories_parent_id_categories"),
        "categories",
        type_="foreignkey",
    )
    op.create_foreign_key(
        op.f("fk_categories_parent_id_categories"),
        "categories",
        "categories",
        ["parent_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.create_index(
        "uq_photos_one_main_per_item",
        "photos",
        ["item_id"],
        unique=True,
        postgresql_where=sa.text("is_main IS TRUE"),
    )

    op.drop_constraint(
        op.f("ck_support_messages_ck_support_messages_sender_consistent"),
        "support_messages",
        type_="check",
    )

    for enum_name, pairs in {
        "admin_role": [("OWNER", "owner"), ("ADMIN", "admin"), ("MANAGER", "manager")],
        "rental_status": [
            ("REQUESTED", "requested"),
            ("IN_PROGRESS", "in_progress"),
            ("CONFIRMED", "confirmed"),
            ("REJECTED", "rejected"),
            ("COMPLETED", "completed"),
            ("CANCELLED_BY_CLIENT", "cancelled_by_client"),
            ("CANCELLED_BY_ADMIN", "cancelled_by_admin"),
        ],
        "review_status": [("PENDING", "pending"), ("PUBLISHED", "published"), ("HIDDEN", "hidden"), ("REJECTED", "rejected")],
        "support_ticket_status": [("OPEN", "open"), ("CLOSED", "closed")],
        "support_message_sender_type": [("USER", "user"), ("ADMIN", "admin"), ("SYSTEM", "system")],
    }.items():
        for old_value, new_value in pairs:
            _rename_enum_value(enum_name, old_value, new_value)

    op.create_check_constraint(
        op.f("ck_support_messages_ck_support_messages_sender_consistent"),
        "support_messages",
        "(sender_type = 'user' AND sender_user_id IS NOT NULL AND sender_admin_id IS NULL) "
        "OR (sender_type = 'admin' AND sender_admin_id IS NOT NULL AND sender_user_id IS NULL) "
        "OR (sender_type = 'system')",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("ck_support_messages_ck_support_messages_sender_consistent"),
        "support_messages",
        type_="check",
    )

    for enum_name, pairs in {
        "support_message_sender_type": [("system", "SYSTEM"), ("admin", "ADMIN"), ("user", "USER")],
        "support_ticket_status": [("closed", "CLOSED"), ("open", "OPEN")],
        "review_status": [("rejected", "REJECTED"), ("hidden", "HIDDEN"), ("published", "PUBLISHED"), ("pending", "PENDING")],
        "rental_status": [
            ("cancelled_by_admin", "CANCELLED_BY_ADMIN"),
            ("cancelled_by_client", "CANCELLED_BY_CLIENT"),
            ("completed", "COMPLETED"),
            ("rejected", "REJECTED"),
            ("confirmed", "CONFIRMED"),
            ("in_progress", "IN_PROGRESS"),
            ("requested", "REQUESTED"),
        ],
        "admin_role": [("manager", "MANAGER"), ("admin", "ADMIN"), ("owner", "OWNER")],
    }.items():
        for old_value, new_value in pairs:
            _rename_enum_value(enum_name, old_value, new_value)

    op.create_check_constraint(
        op.f("ck_support_messages_ck_support_messages_sender_consistent"),
        "support_messages",
        "(sender_type = 'USER' AND sender_user_id IS NOT NULL AND sender_admin_id IS NULL) "
        "OR (sender_type = 'ADMIN' AND sender_admin_id IS NOT NULL AND sender_user_id IS NULL) "
        "OR (sender_type = 'SYSTEM')",
    )

    op.drop_index(
        "uq_photos_one_main_per_item",
        table_name="photos",
        postgresql_where=sa.text("is_main IS TRUE"),
    )

    op.drop_constraint(
        op.f("fk_categories_parent_id_categories"),
        "categories",
        type_="foreignkey",
    )
    op.create_foreign_key(
        op.f("fk_categories_parent_id_categories"),
        "categories",
        "categories",
        ["parent_id"],
        ["id"],
        ondelete="CASCADE",
    )