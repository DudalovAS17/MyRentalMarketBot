from __future__ import annotations

from typing import Optional
from sqlalchemy import Integer, String, Index, JSON
from sqlalchemy.orm import Mapped, mapped_column

from db.models.base import Base, TimestampMixin, ReprMixin, DictMixin

class AdminAction(Base, TimestampMixin, ReprMixin, DictMixin):
    """Audit log действий админа.
    Хранит: кто, что сделал, над какой сущностью, когда и с какими данными."""

    __tablename__ = "admin_actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # telegram_id (TG ID), не user.id (внутренний ID пользователя)!
    admin_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    action_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # Например: "rental", "item", "user", "complaint", "support_ticket"
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)

    # Универсальный ID сущности (на будущее — может быть не только int)
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # Короткая человеко-читаемая заметка (опционально)
    note: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Детали (reason/resolution/previous_status/metadata)
    payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        Index("ix_admin_actions_entity", "entity_type", "entity_id"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "admin_id": self.admin_id,
            "action_type": self.action_type,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "note": self.note,
            "payload": self.payload,
            "created_at": getattr(self, "created_at", None),
        }