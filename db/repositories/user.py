from typing import Optional
from sqlalchemy import select, exists, update
from decimal import Decimal

from db.models.user import User
from db.repositories.base import BaseRepository

from schemas.user import UserCreate, UserUpdate, UserAdminUpdate


class UserRepository(BaseRepository):
    """Репозиторий пользователей"""

    # ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    async def list_all(self, *, limit: Optional[int] = None, offset: int = 0) -> list[User]:
        """Вернуть список пользователей по id по возрастанию"""
        async with self._session() as s:
            stmt = select(User).order_by(User.id)
            if limit is not None:
                stmt = stmt.limit(limit).offset(offset)

            # stmt = select(User).order_by(User.id).offset(offset)
            # if limit is not None:
            #     stmt = stmt.limit(limit)

            return await self._list(s, stmt)

    async def get_by_id(self, user_id: int) -> Optional[User]:
        """Найти пользователя по id"""
        async with self._session() as s:
            return await s.get(User, user_id)

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Найти пользователя по Telegram ID"""
        async with self._session() as s:
            stmt = select(User).where(User.telegram_id == telegram_id)
            return await self._one_or_none(s, stmt)

    async def exists_by_telegram_id(self, telegram_id: int) -> bool:
        """Проверить существование пользователя по Telegram ID"""
        async with self._session() as s:
            stmt = select(exists().where(User.telegram_id == telegram_id))
            return await self._exists(s, stmt)

    # ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    async def create(self, user_data: UserCreate) -> User:
        """Создать нового пользователя"""
        obj = User(**user_data.model_dump())
        async with self._session() as s:
            return await self._add_commit_refresh(s, obj)

    async def update(self, user_id: int, update_data: UserUpdate | UserAdminUpdate) -> Optional[User]:
        """Обновить данные пользователя (только переданные поля)"""
        async with self._session() as s:
            obj: Optional[User] = await s.get(User, user_id)
            if not obj:
                return None

            data = update_data.model_dump(exclude_unset=True)
            if not data:
                return obj

            for k, v in data.items():
                setattr(obj, k, v)

            return await self._commit_refresh(s, obj)

    async def delete(self, user_id: int) -> bool:
        """Удалить пользователя по id.

        Возвращает True — если удалён.
        Возвращает False — если не найден.
        """
        async with self._session() as s:
            obj = await s.get(User, user_id)
            if not obj:
                return False

            return await self._delete_commit(s, obj)

    # ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    async def update_rating(self, *, user_id: int, rating: Decimal, rating_count: int) -> bool:
        """Обновить кеш рейтинга пользователя. Возвращает True, если строка обновлена."""
        async with self._session() as s:
            stmt = (
                update(User)
                .where(User.id == user_id)
                .values(rating=rating, rating_count=rating_count)
            )
            return await self._execute_update_commit(s, stmt)