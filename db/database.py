import logging
from typing import Callable
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker, AsyncEngine

from config import settings
from db.models.base import Base

logger = logging.getLogger(__name__)

class _DatabaseState:
    """Внутренний объект для хранения состояния подключения к базе"""
    def __init__(self) -> None:
        self.engine: AsyncEngine | None = None
        self.session_factory: async_sessionmaker[AsyncSession] | None = None

_db_state = _DatabaseState()

def get_database_url() -> str:
    return settings.database_url

async def init_db(*, create_tables: bool = False) -> None:
    """Инициализация подключения к БД и создание таблиц"""

    if _db_state.engine is not None and _db_state.session_factory is not None:
        logger.info("init_db(): база уже инициализирована")
        return

    database_url = get_database_url()
    _db_state.engine = create_async_engine(database_url, echo=False, future=True, pool_pre_ping=True)
    _db_state.session_factory = async_sessionmaker(bind=_db_state.engine, autoflush=False, autocommit=False, expire_on_commit=False)

    if create_tables: # У нас теперь False - сюда не попадем. Таблицы не будут создаваться тут
        async with _db_state.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("init_db(): таблицы созданы (create_all)")

def get_session_factory() -> Callable[[], AsyncSession]:
    """Фабрика сессий (для репозиториев)"""
    if _db_state.session_factory is None:
        raise RuntimeError("База данных не инициализирована. Сначала вызови init_db().")
    return _db_state.session_factory

async def check_db_connection() -> bool:
    """Одноразово проверить доступность БД через SELECT 1.

    Используется перед основной инициализацией подключения к базе
    """

    database_url = get_database_url()
    async_test_engine = create_async_engine(database_url, future=True, pool_pre_ping=True)

    try:
        async with async_test_engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            ok = result.scalar() == 1
        await async_test_engine.dispose()
        return ok
    except Exception as e:
        logger.error("check_db_connection(): Ошибка при проверке подключения к базе данных: %s", e, exc_info=True)
        return False
    finally:
        await async_test_engine.dispose()

async def close_db() -> None:
    """Аккуратное закрытие engine (на shutdown)"""

    if _db_state.engine is not None:
        await _db_state.engine.dispose()

    _db_state.engine = None
    _db_state.session_factory = None