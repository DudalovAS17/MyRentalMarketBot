# Базовый класс для всех моделей SQLAlchemy
from __future__ import annotations # ???
from typing import Optional, Any
from datetime import datetime

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


# ↓ опциональные, но очень удобные миксины — можно подключать в нужных моделях

class TimestampMixin:
    """Автоматические created_at / updated_at (ставит БД)"""
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(), server_default=func.now() # DateTime(timezone=True)
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(), server_default=func.now(), onupdate=func.now() # DateTime(timezone=True)
    )


class ReprMixin:
    """ModelName(id=1, ...). Показывает PK и пару полей"""
    def __repr__(self) -> str:
        mapper = sa_inspect(self).mapper
        keys = [col.key for col in mapper.primary_key] or [c.key for c in mapper.column_attrs[:2]] # PK или, если нет — первые 2 колонки
        parts = []
        for k in keys:
            try:
                parts.append(f"{k}={getattr(self, k)!r}")
            except Exception:
                pass
        return f"<{self.__class__.__name__} " + ", ".join(parts) + ">"


class DictMixin:
    """to_dict() для всех колонок без связей """
    def to_dict(self) -> dict[str, Any]:
        mapper = sa_inspect(self).mapper
        return {c.key: getattr(self, c.key) for c in mapper.column_attrs}

