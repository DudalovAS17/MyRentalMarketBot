from typing import Optional
from sqlalchemy import select, exists

from db.models.user import User
from db.repositories.base import BaseRepository

from schemas.user import UserCreate, UserUpdate, UserAdminUpdate
from status.user_status import AccountStatus

"""Удален: update_rating - Обновить кеш рейтинга пользователя

list_by_account_status(...) - быстро получать:
- активных клиентов
- заблокированных клиентов

В create() пока так:
        obj = User(**user_data.model_dump())
        #obj = User(**user_data.model_dump(exclude_none=True))

Сейчас delete() физически удаляет клиента.
Для реального RentalMarketBot лучше использовать: account_status = BANNED
"""

class UserRepository(BaseRepository):
    """Репозиторий клиентов."""

    # ───────────────────────────────────────────────────────────────────────────────────────────────────────
    @staticmethod
    def _apply_account_status_filter(stmt, status: AccountStatus):
        """Оставить только клиентов с указанным статусом аккаунта."""
        return stmt.where(User.account_status == status)

    @staticmethod
    def _apply_id_order(stmt):
        """Стабильный порядок выдачи клиентов."""
        return stmt.order_by(User.id.asc())

    @staticmethod
    def _apply_pagination(stmt, *, limit: Optional[int], offset: int):
        if limit is not None:
            stmt = stmt.limit(limit).offset(offset)
        return stmt

    # ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    async def list_all(self, *, limit: Optional[int] = None, offset: int = 0) -> list[User]:
        """Вернуть список клиентов по id по возрастанию."""
        async with self._session() as s:
            stmt = select(User)
            stmt = self._apply_id_order(stmt)
            stmt = self._apply_pagination(stmt, limit=limit, offset=offset)

            return await self._list(s, stmt)

    async def list_by_acc_status(self, status: AccountStatus, *, limit: Optional[int] = None, offset: int = 0) -> list[User]:
        """Вернуть клиентов с указанным статусом аккаунта."""
        async with self._session() as s:
            stmt = select(User)
            stmt = self._apply_account_status_filter(stmt, status)
            stmt = self._apply_id_order(stmt)
            stmt = self._apply_pagination(stmt, limit=limit, offset=offset)

            return await self._list(s, stmt)

    async def get_by_id(self, user_id: int) -> Optional[User]:
        """Найти клиента по id."""
        async with self._session() as s:
            return await s.get(User, user_id)

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Найти клиента по Telegram ID."""
        async with self._session() as s:
            stmt = select(User).where(User.telegram_id == telegram_id)
            return await self._one_or_none(s, stmt)

    async def exists_by_telegram_id(self, telegram_id: int) -> bool:
        """Проверить существование клиента по Telegram ID."""
        async with self._session() as s:
            stmt = select(exists().where(User.telegram_id == telegram_id))
            return await self._exists(s, stmt)

    # ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    async def create(self, user_data: UserCreate) -> User:
        """Создать нового клиента."""
        obj = User(**user_data.model_dump())
        #obj = User(**user_data.model_dump(exclude_none=True))
        async with self._session() as s:
            return await self._add_commit_refresh(s, obj)

    async def update(self, user_id: int, update_data: UserUpdate | UserAdminUpdate) -> Optional[User]:
        """Обновить данные клиента или админские поля аккаунта."""
        async with self._session() as s:
            obj: Optional[User] = await s.get(User, user_id)
            if not obj:
                return None

            data = update_data.model_dump(exclude_unset=True)
            if not data:
                return obj

            changed = False
            for field_name, value in data.items():
                if getattr(obj, field_name) != value:
                    setattr(obj, field_name, value)
                    changed = True

            if not changed:
                return obj

            return await self._commit_refresh(s, obj)

    async def delete(self, user_id: int) -> bool:
        """Удалить клиента по id."""
        async with self._session() as s:
            obj = await s.get(User, user_id)
            if not obj:
                return False

            return await self._delete_commit(s, obj)