import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from config import settings
from db.models.base import Base

# ВАЖНО: импортируем ВСЕ модели, чтобы Alembic увидел их в metadata
import db.models  # noqa: F401

# Alembic Config
config = context.config

# Логирование Alembic
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata для autogenerate
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Запуск миграций в offline-режиме (без подключения к БД)."""
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True, # полезно для изменений типов
        compare_server_default=True, # полезно для дефолтов
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Синхронная часть миграций (Alembic так устроен)."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Запуск миграций к БД в online-режиме (через async engine)."""

    # alembic_cfg = {"sqlalchemy.url": DATABASE_URL}

    alembic_cfg = config.get_section(config.config_ini_section) or {}
    alembic_cfg["sqlalchemy.url"] = settings.database_url

    connectable = async_engine_from_config(
        alembic_cfg,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        # future=True,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations() -> None:
    if context.is_offline_mode():
        run_migrations_offline()
    else:
        asyncio.run(run_migrations_online())

run_migrations()