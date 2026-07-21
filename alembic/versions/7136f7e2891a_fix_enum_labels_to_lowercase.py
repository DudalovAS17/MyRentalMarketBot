"""fix enum labels to lowercase

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-07-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '7136f7e2891a'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _quote_ident(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _quote_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _enum_label_exists(enum_name: str, label: str) -> bool:
    bind = op.get_bind()
    result = bind.execute(
        sa.text(
            """
            SELECT EXISTS (
                SELECT 1
                FROM pg_enum e
                JOIN pg_type t ON t.oid = e.enumtypid
                WHERE t.typname = :enum_name
                  AND e.enumlabel = :label
            )
            """
        ),
        {"enum_name": enum_name, "label": label},
    )
    return bool(result.scalar())


def _get_enum_columns(enum_name: str) -> list[tuple[str, str, str]]:
    """Найти все колонки, использующие PostgreSQL enum type."""
    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            """
            SELECT table_schema, table_name, column_name
            FROM information_schema.columns
            WHERE udt_name = :enum_name
              AND table_schema = 'public'
            ORDER BY table_name, column_name
            """
        ),
        {"enum_name": enum_name},
    ).fetchall()

    return [(row[0], row[1], row[2]) for row in rows]


def _update_enum_column_values(enum_name: str, old_value: str, new_value: str) -> None:
    """Обновить данные в колонках, если enum содержит и старый, и новый label."""
    for schema_name, table_name, column_name in _get_enum_columns(enum_name):
        op.execute(
            sa.text(
                f"""
                UPDATE {_quote_ident(schema_name)}.{_quote_ident(table_name)}
                SET {_quote_ident(column_name)} = {_quote_literal(new_value)}::{_quote_ident(enum_name)}
                WHERE {_quote_ident(column_name)}::text = {_quote_literal(old_value)}
                """
            )
        )


def _rename_enum_value(enum_name: str, old_value: str, new_value: str) -> None:
    """Переименовать enum label, если это безопасно.

    Сценарии:
    - old есть, new нет: RENAME VALUE.
    - old есть, new есть: обновляем строки old -> new, старый label остаётся неиспользованным.
    - old нет, new есть: уже исправлено.
    - old нет, new нет: ничего не делаем.
    """
    old_exists = _enum_label_exists(enum_name, old_value)
    new_exists = _enum_label_exists(enum_name, new_value)

    if old_exists and not new_exists:
        op.execute(
            sa.text(
                f"ALTER TYPE {_quote_ident(enum_name)} "
                f"RENAME VALUE {_quote_literal(old_value)} "
                f"TO {_quote_literal(new_value)}"
            )
        )
        return

    if old_exists and new_exists:
        _update_enum_column_values(enum_name, old_value, new_value)


def _drop_support_message_sender_check() -> None:
    op.execute(
        sa.text(
            """
            ALTER TABLE support_messages
            DROP CONSTRAINT IF EXISTS ck_support_messages_ck_support_messages_sender_consistent
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE support_messages
            DROP CONSTRAINT IF EXISTS ck_support_messages_sender_consistent
            """
        )
    )


def _create_support_message_sender_check_lowercase() -> None:
    op.create_check_constraint(
        "ck_support_messages_sender_consistent",
        "support_messages",
        "(sender_type = 'user' AND sender_user_id IS NOT NULL AND sender_admin_id IS NULL) "
        "OR (sender_type = 'admin' AND sender_admin_id IS NOT NULL AND sender_user_id IS NULL) "
        "OR (sender_type = 'system')",
    )


def _create_support_message_sender_check_uppercase() -> None:
    op.create_check_constraint(
        "ck_support_messages_sender_consistent",
        "support_messages",
        "(sender_type = 'USER' AND sender_user_id IS NOT NULL AND sender_admin_id IS NULL) "
        "OR (sender_type = 'ADMIN' AND sender_admin_id IS NOT NULL AND sender_user_id IS NULL) "
        "OR (sender_type = 'SYSTEM')",
    )


def upgrade() -> None:
    # На время переименования sender_type убираем CHECK,
    # чтобы он не мешал переходу USER/ADMIN/SYSTEM -> user/admin/system.
    _drop_support_message_sender_check()

    enum_renames = {
        "admin_role": [
            ("OWNER", "owner"),
            ("ADMIN", "admin"),
            ("MANAGER", "manager"),
        ],
        "item_status": [
            ("DRAFT", "draft"),
            ("ACTIVE", "active"),
            ("HIDDEN", "hidden"),
            ("ARCHIVED", "archived"),
        ],
        "rental_status": [
            ("REQUESTED", "requested"),
            ("IN_PROGRESS", "in_progress"),
            ("CONFIRMED", "confirmed"),
            ("REJECTED", "rejected"),
            ("COMPLETED", "completed"),
            ("CANCELLED_BY_CLIENT", "cancelled_by_client"),
            ("CANCELLED_BY_ADMIN", "cancelled_by_admin"),
        ],
        "review_status": [
            ("PENDING", "pending"),
            ("PUBLISHED", "published"),
            ("HIDDEN", "hidden"),
            ("REJECTED", "rejected"),
        ],
        "support_ticket_status": [
            ("OPEN", "open"),
            ("CLOSED", "closed"),
        ],
        "support_message_sender_type": [
            ("USER", "user"),
            ("ADMIN", "admin"),
            ("SYSTEM", "system"),
        ],
    }

    for enum_name, pairs in enum_renames.items():
        for old_value, new_value in pairs:
            _rename_enum_value(enum_name, old_value, new_value)

    _create_support_message_sender_check_lowercase()


def downgrade() -> None:
    _drop_support_message_sender_check()

    enum_renames = {
        "support_message_sender_type": [
            ("system", "SYSTEM"),
            ("admin", "ADMIN"),
            ("user", "USER"),
        ],
        "support_ticket_status": [
            ("closed", "CLOSED"),
            ("open", "OPEN"),
        ],
        "review_status": [
            ("rejected", "REJECTED"),
            ("hidden", "HIDDEN"),
            ("published", "PUBLISHED"),
            ("pending", "PENDING"),
        ],
        "rental_status": [
            ("cancelled_by_admin", "CANCELLED_BY_ADMIN"),
            ("cancelled_by_client", "CANCELLED_BY_CLIENT"),
            ("completed", "COMPLETED"),
            ("rejected", "REJECTED"),
            ("confirmed", "CONFIRMED"),
            ("in_progress", "IN_PROGRESS"),
            ("requested", "REQUESTED"),
        ],
        "item_status": [
            ("archived", "ARCHIVED"),
            ("hidden", "HIDDEN"),
            ("active", "ACTIVE"),
            ("draft", "DRAFT"),
        ],
        "admin_role": [
            ("manager", "MANAGER"),
            ("admin", "ADMIN"),
            ("owner", "OWNER"),
        ],
    }

    for enum_name, pairs in enum_renames.items():
        for old_value, new_value in pairs:
            _rename_enum_value(enum_name, old_value, new_value)

    _create_support_message_sender_check_uppercase()