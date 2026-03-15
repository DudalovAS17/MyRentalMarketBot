import logging
from typing import Optional, FrozenSet
from datetime import datetime, timezone

from db.repositories.user import UserRepository
from schemas.user import UserCreate, UserUpdate, UserOut, UserAdminUpdate
from status.user_status import can_transition, AccountStatus
from utils.errors import NotFoundError, ServiceError, ConflictError, ForbiddenError

logger = logging.getLogger(__name__)

class UserService:
    """Сервис для работы с пользователями"""

    def __init__(self, repo: UserRepository, admin_ids: FrozenSet[int]) -> None:
        self.repo = repo
        self._admin_ids = admin_ids

    def _is_admin(self, tg_user_id: int) -> bool:
        return tg_user_id in self._admin_ids

    async def get_by_id(self, user_id: int, *, strict: bool = False) -> Optional[UserOut]:
        """Найти пользователя по ID"""
        user = await self.repo.get_by_id(user_id)
        if not user:
            if strict:
                raise NotFoundError(f"User not found: id={user_id}")
            return None

        return UserOut.model_validate(user)

    async def get_by_telegram_id(self, telegram_id: int, *, strict: bool = False) -> Optional[UserOut]:
        """Найти пользователя по Telegram ID"""
        user = await self.repo.get_by_telegram_id(telegram_id)
        if not user:
            if strict:
                raise NotFoundError(f"User not found: tg_id={telegram_id}")
            return None

        return UserOut.model_validate(user)

    async def list_all(self) -> list[UserOut]:
        """Получить всех пользователей"""
        users = await self.repo.list_all()
        return [UserOut.model_validate(o) for o in users]

    # ────────────────────────────────────────────────────────────────────────────────────────────────
    async def create(self, user_data: UserCreate) -> UserOut:
        """Создать нового пользователя"""
        user = await self.repo.create(user_data)

        dto = UserOut.model_validate(user)
        logger.info("User created id=%s telegram_id=%s", dto.id, dto.telegram_id)
        return dto

    async def update(self, user_id: int, update_data: UserUpdate, *, strict: bool = False) -> Optional[UserOut]:
        """Обновить данные пользователя"""
        user = await self.repo.update(user_id, update_data)
        if not user:
            if strict:
                raise NotFoundError(f"Пользователь не найден: id={user_id}")
            return None

        dto = UserOut.model_validate(user)
        logger.info("User updated id=%s", dto.id)
        return dto

    async def delete(self, user_id: int, *, strict: bool = False) -> bool:
        """Удалить пользователя"""
        deleted = await self.repo.delete(user_id)
        if not deleted:
            if strict:
                raise NotFoundError(f"Пользователь не найден: id={user_id}")
            return False

        logger.info("User deleted id=%s", user_id)
        return True

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    async def register_or_update_user(self, user_data: UserCreate) -> UserOut:
        """Регистрация: создаёт пользователя или обновляет, если уже есть"""
        existing = await self.repo.get_by_telegram_id(user_data.telegram_id)
        payload = user_data.model_dump(exclude_unset=True) # exclude_unset=True вынести?

        if existing: # если найден → обновляем
            logger.info("Пользователь с telegram_id=%s уже существует → обновляем", user_data.telegram_id)
            updated = await self.repo.update(existing.id, UserUpdate(**payload))
            if not updated:
                raise ServiceError(f"Не удалось обновить пользователя id={existing.id}")

            return UserOut.model_validate(updated)

        # если не найден → создаём
        created = await self.repo.create(user_data)
        if not created:
            raise ServiceError(f"Не удалось создать пользователя telegram_id={user_data.telegram_id}")
        logger.info("Created new user telegram_id=%s id=%s", created.telegram_id, created.id)

        return UserOut.model_validate(created)

    # ──────────────────────────────────────────── NEW (Admin-User logic) ────────────────────────────────────────
    async def ban_user(self, *, user_id: int, admin_user_id: int, reason: str, strict: bool = False) -> Optional[UserOut]:
        """Заблокировать пользователя с записью причины"""
        if user_id == admin_user_id: # это БД или тг id?
            raise ConflictError("Нельзя забанить самого себя")

        user = await self.repo.get_by_id(user_id)
        if not user:
            if strict:
                raise NotFoundError(f"Пользователь не найден: id={user_id}")
            return None

        if self._is_admin(user.telegram_id): # избавились от user.is_admin
            raise ForbiddenError("Нельзя забанить администратора")

        current_status = user.account_status
        if not can_transition(current_status, AccountStatus.BANNED):
            if strict:
                # Нельзя забанить пользователя: статус изменился или переход запрещён
                raise ConflictError(f"Transition {current_status} -> {AccountStatus.BANNED} is not allowed")
            return None

        update_data = UserAdminUpdate(
            account_status=AccountStatus.BANNED,
            banned_at=datetime.now(timezone.utc),
            banned_by_admin_id=admin_user_id,
            ban_reason=reason,
            is_blocked=True # Уберем в будущем, т.к. дублирует account_status
        )

        updated = await self.repo.update(user_id, update_data)
        if not updated:
            if strict:
                raise ConflictError("Не удалось обновить пользователя")
            return None

        return UserOut.model_validate(updated)

    async def unban_user(self, user_id: int, strict: bool = False) -> Optional[UserOut]:
        """Разблокировать пользователя."""
        user = await self.repo.get_by_id(user_id)
        if not user:
            if strict:
                raise NotFoundError(f"Пользователь не найден: id={user_id}")
            return None

        current_status = user.account_status
        if not can_transition(current_status, AccountStatus.ACTIVE):
            if strict:
                # Нельзя разбанить пользователя: статус изменился или переход запрещён
                raise ConflictError(f"Transition {current_status} -> {AccountStatus.ACTIVE} is not allowed")
            return None

        update_data = UserAdminUpdate(
            account_status=AccountStatus.ACTIVE,
            #banned_at=datetime.now(timezone.utc),
            #banned_by_admin_id=None,
            #ban_reason=None,
            is_blocked=False # Уберем в будущем, т.к. дублирует account_status
        )

        updated = await self.repo.update(user_id, update_data)
        if not updated:
            if strict:
                raise ConflictError("Не удалось обновить пользователя")
            return None

        return UserOut.model_validate(updated)
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    async def check_user_exists(self, telegram_id: int) -> bool:
        """Проверяет, существует ли пользователь с данным Telegram ID"""
        return await self.repo.exists_by_telegram_id(telegram_id)

    async def is_user_blocked(self, telegram_id: int, *, strict: bool = False) -> Optional[bool]:
        """
        True  — пользователь заблокирован (account_status == BANNED)
        False — не заблокирован
        None  — не найден (если strict=False)
        """
        user = await self.repo.get_by_telegram_id(telegram_id)
        if not user:
            if strict:
                raise NotFoundError(f"Пользователь не найден: tg_id={telegram_id}")
            return None

        return user.account_status == AccountStatus.BANNED