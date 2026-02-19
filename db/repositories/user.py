from __future__ import annotations

from typing import Callable, Optional, List, Union
from sqlalchemy import select, exists, update
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.user import User
from schemas.user import UserCreate, UserUpdate, UserAdminUpdate


class UserRepository:
    """Репозиторий пользователей"""

    def __init__(self, session_factory: Callable[[], AsyncSession]) -> None:
        self._sf = session_factory

    async def list_all(self, *, limit: Optional[int] = None, offset: int = 0) -> List[User]:
        """Вернуть список пользователей по id по возрастанию"""
        async with self._sf() as s:
            stmt = select(User).order_by(User.id)
            if limit is not None:
                stmt = stmt.limit(limit).offset(offset)

            # stmt = select(User).order_by(User.id).offset(offset)
            # if limit is not None:
            #     stmt = stmt.limit(limit)

            res = await s.execute(stmt)
            return list(res.scalars())

    async def get_by_id(self, user_id: int) -> Optional[User]:
        """Найти пользователя по id. Возвращает User или None."""
        async with self._sf() as s:
            return await s.get(User, user_id)

    async def get_by_telegram_id(self, telegram_id: int | str) -> Optional[User]:
        """Найти пользователя по Telegram ID. Возвращает User или None."""
        async with self._sf() as s:
            res = await s.execute(select(User).where(User.telegram_id == telegram_id))
            return res.scalar_one_or_none()

    async def exists_by_telegram_id(self, telegram_id: int) -> bool:
        """Проверить существование пользователя по Telegram ID. Возвращает True или False."""
        async with self._sf() as s:
            res = await s.execute(select(exists().where(User.telegram_id == telegram_id)))
            return bool(res.scalar())

    async def create(self, user_data: UserCreate) -> User:
        """Создать нового пользователя"""

        # Проверка на дубликат по telegram_id (если пользователь уже существует)

        obj = User(**user_data.model_dump())
        async with self._sf() as s:
            s.add(obj)
            try:
                await s.commit()
            except Exception:
                await s.rollback()
                raise
            await s.refresh(obj)
            return obj

    UpdateSchema = Union[UserUpdate, UserAdminUpdate]

    async def update(self, user_id: int, update_data: UpdateSchema) -> Optional[User]:
        """Обновить данные пользователя (только переданные поля)"""
        async with self._sf() as s:
            obj: Optional[User] = await s.get(User, user_id)
            if not obj:
                return None

            data = update_data.model_dump(exclude_unset=True)
            for k, v in data.items():
                setattr(obj, k, v)

            try:
                await s.commit()
            except Exception:
                await s.rollback()
                raise
            await s.refresh(obj)
            return obj

    async def delete(self, user_id: int) -> int:
        """Удалить пользователя по id. Возвращает True — если удалён, False — если не найден"""
        async with self._sf() as s:
            obj = await s.get(User, user_id)
            if not obj:
                return False

            await s.delete(obj)
            try:
                await s.commit()
            except Exception:
                await s.rollback()
                raise
            return True


    # для сервиса отзывов - Обновить рейтинг пользователя
    async def update_rating(self, *, user_id: int, rating: float, rating_count: int) -> bool:
        """Обновить кеш рейтинга пользователя. Возвращает True, если строка обновлена."""
        async with self._sf() as s:
            stmt = (
                update(User)
                .where(User.id == user_id)
                .values(rating=rating, rating_count=rating_count)
            )

            try:
                res = await s.execute(stmt)
                await s.commit()
            except Exception:
                await s.rollback()
                raise

            updated_rows = int(getattr(res, "rowcount", 0) or 0)
            return updated_rows > 0
