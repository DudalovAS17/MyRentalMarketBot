# db/repositories/user_repository.py
from __future__ import annotations
from typing import Callable, Optional, List #, Any, Dict

import logging
from sqlalchemy import select, exists
#from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.user import User
from schemas.user import UserCreate, UserUpdate #, UserOut

logger = logging.getLogger(__name__)


class UserRepository:
    """Репозиторий пользователей. DI: session_factory -> Session."""

    def __init__(self, session_factory: Callable[[], AsyncSession]) -> None:
        self._sf = session_factory

    async def get_all(self, *, limit: Optional[int] = None, offset: int = 0) -> List[User]:
        """Вернуть список пользователей по id по возрастанию"""
        async with self._sf() as s:
            stmt = select(User).order_by(User.id)
            if limit is not None:
                stmt = stmt.limit(limit).offset(offset)
            res = await s.execute(stmt)
            return list(res.scalars())

    async def get_by_id(self, user_id: int) -> Optional[User]:
        """Найти пользователя по id. Возвращает User или None."""
        async with self._sf() as s:
            return await s.get(User, user_id)

    async def get_by_telegram_id(self, telegram_id: int | str) -> Optional[User]:
        """Найти пользователя по Telegram ID. Возвращает User или None."""
        tg = str(telegram_id).strip()
        async with self._sf() as s:
            res = await s.execute(select(User).where(User.telegram_id == tg))
            return res.scalar_one_or_none()

    async def exists_by_telegram_id(self, telegram_id: int | str) -> bool:
        """Проверить существование пользователя по Telegram ID. Возвращает True или False."""
        tg = str(telegram_id).strip()
        async with self._sf() as s:
            res = await s.execute(select(exists().where(User.telegram_id == tg)))
            return bool(res.scalar())

    async def create(self, user_data: UserCreate) -> User:
        """Создать нового пользователя"""

        # Проверка на дубликат по telegram_id (если пользователь уже существует)

        obj = User(**user_data.model_dump())
        async with self._sf() as s:
            s.add(obj)
            try:
                await s.commit()
            except Exception as e:
                await s.rollback() # ???
                logger.error("create() Ошибка при создании пользователя: %s",
                             obj.telegram_id, e, exc_info=True)
                raise

            await s.refresh(obj)
            logger.info("Создан пользователь id=%s telegram_id=%s username=%r",
                        obj.id, obj.telegram_id, obj.username)
            return obj

    async def update(self, user_id: int, update_data: UserUpdate) -> Optional[User]:
        """Обновить данные пользователя (только переданные поля)"""
        async with self._sf() as s:
            obj = await s.get(User, user_id)
            if not obj:
                logger.warning("update() — пользователь с id=%s не найден", user_id)
                return None

            data = update_data.model_dump(exclude_unset=True)
            for k, v in data.items():
                setattr(obj, k, v)

            try:
                await s.commit()
            except Exception as e:
                await s.rollback()
                logger.error("Ошибка при обновлении пользователя %s: %s", user_id, e, exc_info=True)
                raise

            await s.refresh(obj)
            logger.info("Обновлён пользователь id=%s", obj.id)
            return obj

    async def delete(self, user_id: int) -> int:
        """Удалить пользователя по id. Возвращает 1 — если удалён, 0 — если не найден"""
        async with self._sf() as s:
            obj = await s.get(User, user_id)
            if not obj:
                logger.warning("delete() — пользователь с id=%s не найден", user_id)
                return 0

            try:
                await s.delete(obj)
                await s.commit()
                logger.info("delete() — пользователь id=%s успешно удалён", user_id)
                return 1
            except Exception as e:
                await s.rollback()
                logger.error("delete() — ошибка при удалении пользователя id=%s: %s", user_id, e, exc_info=True)
                raise


    # логика отзывов
    async def update_rating(
        self,
        *,
        user_id: int,
        rating: float,
        rating_count: int,
    ) -> User:
        """Обновить рейтинг пользователя"""

        update_data = UserUpdate(
            rating=rating,
            rating_count=rating_count,
        )

        user = await self.update(user_id, update_data)

        if not user:
            raise ValueError(f"User with id={user_id} not found")

        return user
