from __future__ import annotations

import logging

from db.database import check_db_connection, close_db, init_db

logger = logging.getLogger(__name__)

async def init_db_or_fail(*, create_tables: bool = False) -> None:
    """ Инициализация базы данных (Postgres-only bootstrap)

    Production default: create_tables=False
    - In prod you should use Alembic migrations, not create_all at startup.
    """
    ok = await check_db_connection()
    # ✅ Проверяем подключение к БД
    if not ok:
        logger.error("Не удалось подключиться к базе данных")
        raise RuntimeError("Database connection check failed")

    await init_db(create_tables=create_tables)
    logger.info("База данных успешно инициализирована")


async def shutdown_db() -> None:
    """Graceful shutdown hook."""
    await close_db()
    logger.info("Database shutdown completed")