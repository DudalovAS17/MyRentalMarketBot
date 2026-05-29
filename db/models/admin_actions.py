from __future__ import annotations

from typing import Optional, TYPE_CHECKING
from sqlalchemy import ForeignKey, Integer, String, Index, JSON, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from db.models.admins import Admin

class AdminAction(Base, TimestampMixin):
    """Журнал действий администратора."""
    __tablename__ = "admin_actions"

    # идентификатор event-record
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    admin_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("admins.id", ondelete="SET NULL"),
        nullable=True,
    )

    admin_tg_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    # что сделал админ
    action_type: Mapped[str] = mapped_column(String(64), nullable=False)

    # над какой сущностью было действие (rental, item, ..)
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False)

    # Универсальный ID сущности, над которой выполнено действие
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False) # Integer

    # Короткая человеко-читаемая заметка (опционально)
    note: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Детали (reason/resolution/previous_status/metadata)
    payload: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)


    # ------- Отношения | связи --------

    admin: Mapped[Optional["Admin"]] = relationship(
        "Admin",
        back_populates="admin_actions",
    )

    __table_args__ = (
        Index("ix_admin_actions_admin_id", "admin_id"),
        Index("ix_admin_actions_admin_tg_id", "admin_tg_id"),

        Index("ix_admin_actions_action_type", "action_type"),
        Index("ix_admin_actions_entity_type", "entity_type"),
        Index("ix_admin_actions_entity_id", "entity_id"),

        Index("ix_admin_actions_entity", "entity_type", "entity_id"),
        Index("ix_admin_actions_admin_entity", "admin_id", "entity_type", "entity_id"),
    )