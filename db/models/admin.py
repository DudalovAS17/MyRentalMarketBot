from __future__ import annotations

from typing import Optional
from sqlalchemy import Integer, String, Index, JSON, BigInteger
from sqlalchemy.orm import Mapped, mapped_column

from db.models.base import Base, TimestampMixin

class AdminAction(Base, TimestampMixin):
    """Audit log действий админа."""

    __tablename__ = "admin_actions"

    # идентификатор event-record
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    admin_tg_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    # что сделал админ
    action_type: Mapped[str] = mapped_column(String(64), nullable=False)

    # над какой сущностью было действие (rental, item, ..)
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False)

    # Универсальный ID сущности, над которой выполнено действие
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False)

    # Короткая человеко-читаемая заметка (опционально)
    note: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Детали (reason/resolution/previous_status/metadata)
    payload: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        Index("ix_admin_actions_admin_tg_id", "admin_tg_id"),
        Index("ix_admin_actions_action_type", "action_type"),
        Index("ix_admin_actions_entity_type", "entity_type"),
        Index("ix_admin_actions_entity_id", "entity_id"),

        Index("ix_admin_actions_entity", "entity_type", "entity_id"),
    )