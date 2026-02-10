# Базовый класс для всех моделей SQLAlchemy
from __future__ import annotations
from typing import Optional, Any
from datetime import datetime, timezone

from sqlalchemy import MetaData, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import inspect as sa_inspect

# Единые имена для PK/FK/индексов/уникалок (удобно для Alembic и чтения схемы)
NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

class Base(DeclarativeBase):
    """Базовый класс для всех моделей"""
    metadata = MetaData(naming_convention=NAMING_CONVENTION)

class TimestampMixin:
    """Автоматические created_at / updated_at (ставит БД) в UTC (timezone-aware)"""
    created_at: Mapped[datetime] = mapped_column( # Было Mapped[Optional[datetime]]
        DateTime(timezone=True),
        #server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
        nullable=False # Запрещает хранить NULL в колонке на уровне БД. У каждой записи ВСЕГДА есть время создания и обновления.
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        #server_default=func.now(),
        #onupdate=func.now(),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    # 1) Если поле nullable=False, то: rental.created_at - всегда datetime
    #   if rental.created_at is not None:  # ❌ лишний шум
    # 2) Почему Optional[datetime] + nullable=False — плохо
    #       Optional говорит: “может быть None”
    #       nullable=False говорит: “никогда не None”


# class ReprMixin
# class DictMixin

