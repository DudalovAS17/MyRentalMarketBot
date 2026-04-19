import logging

from db.database import check_db_connection, close_db, init_db

logger = logging.getLogger(__name__)

async def init_db_or_fail(*, create_tables: bool = False) -> None:
    """ Инициализация базы данных (Postgres-only bootstrap)"""

    ok = await check_db_connection()
    if not ok:
        logger.error("Не удалось подключиться к базе данных")
        raise RuntimeError("Database connection check failed")

    await init_db(create_tables=create_tables)
    logger.info("База данных успешно инициализирована")

async def shutdown_db() -> None:
    """Shutdown-хук базы данных"""
    await close_db()
    logger.info("Database shutdown completed")