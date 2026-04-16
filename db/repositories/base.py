from contextlib import asynccontextmanager
from typing import Any, Optional, AsyncIterator, Callable
from sqlalchemy import Select, Update
from sqlalchemy.ext.asyncio import AsyncSession


class BaseRepository:
    """Базовый класс — общая логика для всех репозиториев

    Он закрепляет 4 важных инварианта слоя:
        единый session-style через фабрику сессий и context manager
        единый read-style через общие helpers выполнения select
        единый transition-style (безопасный commit с rollback при ошибке)
        единый write-style через безопасный commit с rollback и через повторно используемые helpers для типовых мутаций
    """

    def __init__(self, session_factory: Callable[[], AsyncSession]) -> None:
        """Фабрика сессий"""
        self._sf = session_factory

    @asynccontextmanager
    async def _session(self) -> AsyncIterator[AsyncSession]:
        """единая точка открытия сессии (AsyncSession) через фабрику. Отдаёт сессию как async context manager.

        Используется как:
            async with self._session() as s:
                result = await s.execute(...)
        """
        async with self._sf() as session:
            yield session

    # ────────────────────────────────────────READ-HELPERS──────────────────────────────────────────────────────────────
    @staticmethod
    async def _list(session: AsyncSession, stmt: Select) -> list[Any]:
        res = await session.execute(stmt)
        return list(res.scalars()) # .all())

    @staticmethod
    async def _one_or_none(session: AsyncSession, stmt: Select) -> Optional[Any]:
        res = await session.execute(stmt)
        return res.scalar_one_or_none()

    @staticmethod
    async def _exists(session: AsyncSession, stmt: Select) -> bool:
        res = await session.execute(stmt)
        return bool(res.scalar())

    # ────────────────────────────────────────TRANSITION-HELPER─────────────────────────────────────────────────────────
    @staticmethod
    async def _commit_or_rollback(session: AsyncSession) -> None:
        """Безопасный commit: при ошибке делает rollback и пробрасывает исключение.

        Используется в write-операциях:
            s.add(obj)
            await self._commit_or_rollback(s)
            await s.refresh(obj)
        """
        try:
            await session.commit()
        except Exception:
            await session.rollback()
            raise

    # ────────────────────────────────────────WRITE-HELPER──────────────────────────────────────────────────────────────
    # create
    async def _add_commit_refresh(self, session: AsyncSession, obj):
        session.add(obj)
        await self._commit_or_rollback(session)
        await session.refresh(obj)
        return obj

    # update
    async def _commit_refresh(self, session: AsyncSession, obj):
        await self._commit_or_rollback(session)
        await session.refresh(obj)
        return obj

    # delete
    async def _delete_commit(self, session: AsyncSession, obj):
        await session.delete(obj)
        await self._commit_or_rollback(session)
        return True

    async def _execute_update_commit(self, session: AsyncSession, stmt: Update) -> bool:
        res = await session.execute(stmt)
        await self._commit_or_rollback(session)
        # Костыль, чтобы обойти подчеркивание res.rowcount > 0
        updated_rows = int(getattr(res, "rowcount", 0) or 0)
        return updated_rows > 0
    # ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────