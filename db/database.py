from __future__ import annotations

import logging
from typing import Callable, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
    AsyncEngine,
)

from config import settings
from db.models.base import Base

logger = logging.getLogger(__name__)

async_engine: Optional[AsyncEngine] = None
AsyncSessionLocal: Optional[async_sessionmaker[AsyncSession]] = None # sessionmaker


def _get_database_url() -> str:
    return settings.database_url

async def init_db(*, create_tables: bool = False) -> None: # bool = True
    """ Инициализация подключения к БД и создание таблиц.

    create_tables=True — DEV/MVP режим: создаём таблицы через create_all.
    В PROD режиме (с Alembic) нужно будет вызывать init_db(create_tables=False).
    """
    global async_engine, AsyncSessionLocal

    if async_engine is not None and AsyncSessionLocal is not None:
        logger.info("init_db(): база уже инициализирована")
        return

    database_url = _get_database_url()

    async_engine = create_async_engine(
        database_url,
        echo=False,
        future=True,
        pool_pre_ping=True,  # полезно для Postgres
    )

    AsyncSessionLocal = async_sessionmaker(
        bind=async_engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )

    if create_tables: # у нас теперь False - сюда не попадем. Таблицы не будут создаваться тут
        # DEV/MVP: создаём таблицы (пока без Alembic)
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("init_db(): таблицы созданы (create_all)")


def get_session_factory() -> Callable[[], AsyncSession]:
    """Фабрика сессий (для репозиториев)."""
    if AsyncSessionLocal is None:
        raise RuntimeError("База данных не инициализирована. Сначала вызови init_db().")
    return AsyncSessionLocal


async def check_db_connection() -> bool:
    """Проверка соединения с БД (SELECT 1)."""
    database_url = _get_database_url()
    try:
        async_test_engine = create_async_engine(database_url, future=True, pool_pre_ping=True)
        async with async_test_engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            ok = result.scalar() == 1
        await async_test_engine.dispose()
        return ok
    except Exception as e:
        logger.error("check_db_connection(): Ошибка при проверке подключения к базе данных: %s", e, exc_info=True)
        return False


async def close_db() -> None:
    """Аккуратное закрытие engine (на shutdown)."""
    global async_engine, AsyncSessionLocal

    if async_engine is not None:
        await async_engine.dispose()

    async_engine = None
    AsyncSessionLocal = None