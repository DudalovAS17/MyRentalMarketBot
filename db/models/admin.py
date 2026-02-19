from __future__ import annotations

from typing import Optional
from sqlalchemy import Integer, String, Index, JSON, BigInteger
from sqlalchemy.orm import Mapped, mapped_column

from db.models.base import Base, TimestampMixin

class AdminAction(Base, TimestampMixin):
    """Audit log действий админа."""

    __tablename__ = "admin_actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # именно tg_id, не user_id
    admin_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    action_type: Mapped[str] = mapped_column(String(64), nullable=False) # сервис обязан приводить к str

    entity_type: Mapped[str] = mapped_column(String(32), nullable=False) # сервис обязан приводить к str

    # Универсальный ID сущности
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False) # сервис обязан приводить к str

    # Короткая человеко-читаемая заметка (опционально)
    note: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Детали (reason/resolution/previous_status/metadata)
    payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        Index("ix_admin_actions_admin_id", "admin_id"),
        Index("ix_admin_actions_action_type", "action_type"),
        Index("ix_admin_actions_entity_type", "entity_type"),
        Index("ix_admin_actions_entity_id", "entity_id"),

        Index("ix_admin_actions_entity", "entity_type", "entity_id"),
    )

