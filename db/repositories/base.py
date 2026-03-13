from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, Optional, AsyncIterator, Callable
from sqlalchemy import Select, Update
from sqlalchemy.ext.asyncio import AsyncSession


class BaseRepository:
    """Базовый класс — общая логика для всех репозиториев.

    Предоставляет:
    - self._sf — фабрика сессий (async_sessionmaker)
    - self._session() — context manager для read-операций
    - self._commit_or_rollback(session) — безопасный commit с rollback при ошибке

    return await self._add_commit_refresh(s, obj)
    return await self._commit_refresh(s, obj)
    return await self._delete_commit(s, obj)
    return await self._execute_update_commit(s, stmt)

    return await self._list(s, stmt)
    return await self._one_or_none(s, stmt)
    return await self._exists(s, stmt)
    """

    def __init__(self, session_factory: Callable[[], AsyncSession]) -> None:
        self._sf = session_factory

    @asynccontextmanager
    async def _session(self) -> AsyncIterator[AsyncSession]:
        """Открывает сессию для операции. Используется как:

            async with self._session() as s:
                result = await s.execute(...)
        """
        async with self._sf() as session:
            yield session

    async def _list(self, session: AsyncSession, stmt: Select) -> list[Any]:
        res = await session.execute(stmt)
        return list(res.scalars()) # .all())

    async def _one_or_none(self, session: AsyncSession, stmt: Select) -> Optional[Any]:
        res = await session.execute(stmt)
        return res.scalar_one_or_none()

    async def _exists(self, session: AsyncSession, stmt: Select) -> bool:
        res = await session.execute(stmt)
        return bool(res.scalar())

    # ────────────────────────────────────────create/update/delete──────────────────────────────────────────────────────
    async def _commit_or_rollback(self, session: AsyncSession) -> None:
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

    # либо так obj: Any) -> Any:
    # ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    async def _execute_update_commit(self, session: AsyncSession, stmt: Update) -> bool:
        res = await session.execute(stmt)
        await self._commit_or_rollback(session)
        # Костыль, чтобы обойти подчеркивание res.rowcount > 0
        updated_rows = int(getattr(res, "rowcount", 0) or 0)
        return updated_rows > 0