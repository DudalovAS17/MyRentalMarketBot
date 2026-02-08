import os
import logging
from typing import Callable
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
#from sqlalchemy.orm import sessionmaker, Session

from config import DATABASE_URL
from db.models.base import Base

logger = logging.getLogger(__name__)

# Глобальные объекты
async_engine = None # engine = None
AsyncSessionLocal = None # SessionLocal = None

async def init_db():
    """Инициализация базы данных и создание таблиц"""
    global async_engine, AsyncSessionLocal #engine, SessionLocal

    if async_engine is not None:
        logger.info("База данных уже инициализирована")
        return

    try:
        logger.info(f"Инициализация подключения к базе данных: {DATABASE_URL}")

        # создаём директорию для SQLite (если нужно)
        if DATABASE_URL.startswith("sqlite+aiosqlite:///"):
            db_path = DATABASE_URL.replace("sqlite+aiosqlite:///", "")
            db_dir = os.path.dirname(db_path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
                logger.info(f"Создана директория для базы данных: {db_dir}")

        async_engine = create_async_engine(
            DATABASE_URL,
            echo=False,  # ставь True, если хочешь логировать SQL-запросы
            future=True
        )
        AsyncSessionLocal = async_sessionmaker(
            bind=async_engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False
        )

        # создаём таблицы, если их нет
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        # Base.metadata.create_all(bind=async_engine)
        logger.info("База данных успешно инициализирована.")

    except Exception as e:
        logger.error(f"Ошибка при инициализации базы данных: {e}", exc_info=True)
        async_engine = None
        AsyncSessionLocal = None
        raise

def get_session_factory() -> Callable[[], AsyncSession]: # get_db() -> Session:
    """Вернуть фабрику сессий (для репозиториев)"""
    if AsyncSessionLocal is None:
        raise RuntimeError("База данных не инициализирована. Сначала вызови init_db().")
    return AsyncSessionLocal

async def check_db_connection() -> bool:
    """Проверка соединения с БД."""
    try:
        async_test_engine = create_async_engine(DATABASE_URL, future=True)
        async with async_test_engine.connect() as conn:
            result = await conn.execute(text("SELECT 1")) #.scalar()
            return result.scalar() == 1
    except Exception as e:
        logger.error(f"Ошибка при проверке подключения к базе данных: {e}", exc_info=True)
        return False
