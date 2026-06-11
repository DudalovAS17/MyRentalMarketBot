from __future__ import annotations

from datetime import datetime
from typing import Final
from sqlalchemy import MetaData, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


NAMING_CONVENTION: Final[dict[str, str]] = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

class Base(DeclarativeBase):
    """Базовый класс для всех SQLAlchemy моделей"""
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class TimestampMixin:
    """Автоматические created_at / updated_at (ставит БД) в UTC (timezone-aware)

    - created_at: выставляется БД (server-side), чтобы время было консистентным независимо от хоста приложения.
    - updated_at: выставляется на update (server-side).
    """
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )