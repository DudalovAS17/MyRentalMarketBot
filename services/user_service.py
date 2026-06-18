import logging
from enum import StrEnum
from typing import Optional, FrozenSet
from dataclasses import dataclass
from datetime import datetime, timezone

from db.repositories.user import UserRepository

from schemas.user import UserCreate, UserUpdate, UserOut, UserAdminUpdate
from status.user_status import can_transition, AccountStatus
from utils.errors import NotFoundError, ServiceError, ConflictError, ForbiddenError, ValidationError

logger = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────
class StartAction(StrEnum):
    REGISTER = "register"
    NEED_PHONE = "need_phone"
    ACCESS_BLOCKED = "access_blocked"
    MAIN_MENU = "main_menu"

@dataclass(slots=True)
class StartEntryResult:
    action: StartAction
    user: UserOut | None = None

def can_use_bot(status: AccountStatus) -> bool:
    """Проверить, может ли пользователь пользоваться ботом"""
    return status == AccountStatus.ACTIVE
# ────────────────────────────────────────────────────────


class UserService:
    """Сервис для работы с клиентами"""

    def __init__(self, repo: UserRepository, admin_ids: FrozenSet[int]) -> None:
        self.repo = repo
        self._admin_ids = admin_ids

    # ────────────────────────────────────────── DTO helpers ──────────────────────────────────────────────────────────
    @staticmethod
    def _to_out(user) -> UserOut:
        return UserOut.model_validate(user)

    @classmethod
    def _to_out_list(cls, users) -> list[UserOut]:
        return [cls._to_out(user) for user in users]

    # ─────────────────────────────────────── Business validation ─────────────────────────────────────────────────────
    def _is_admin_telegram_id(self, telegram_id: int) -> bool:
        """Проверить, входит ли Telegram ID в whitelist сотрудников компании."""
        return telegram_id in self._admin_ids

    @staticmethod
    def _validate_telegram_id(telegram_id: int) -> None:
        if telegram_id <= 0:
            raise ValidationError("Некорректный Telegram ID клиента")

    @staticmethod
    def _validate_ban_reason(reason: str) -> str:
        normalized = reason.strip()
        if not normalized:
            raise ValidationError("Причина блокировки клиента не может быть пустой")
        return normalized

    # ────────────────────────────────────────── Read methods ──────────────────────────────────────────────────────────
    async def get_by_id(self, user_id: int, *, strict: bool = False) -> Optional[UserOut]:
        """Найти клиента по ID"""
        user = await self.repo.get_by_id(user_id)
        if not user:
            if strict:
                raise NotFoundError(f"Клиент не найден: id={user_id}")
            return None

        return self._to_out(user)

    async def get_by_telegram_id(self, telegram_id: int, *, strict: bool = False) -> Optional[UserOut]:
        """Найти клиента по Telegram ID"""
        user = await self.repo.get_by_telegram_id(telegram_id)
        if not user:
            if strict:
                raise NotFoundError(f"Клиент не найден: tg_id={telegram_id}")
            return None

        return self._to_out(user)

    async def list_all(self, *, limit: Optional[int] = None, offset: int = 0) -> list[UserOut]:
        """Получить клиентов с пагинацией."""
        users = await self.repo.list_all(limit=limit, offset=offset)
        return self._to_out_list(users)

    async def list_by_account_status(self, status: AccountStatus, *, limit: Optional[int] = None, offset: int = 0) -> list[UserOut]:
        """Получить клиентов с указанным статусом аккаунта."""
        users = await self.repo.list_by_acc_status(status=status, limit=limit, offset=offset)
        return self._to_out_list(users)

    # ─────────────────────────────────────────── write methods ────────────────────────────────────────────────────────
    async def create(self, user_data: UserCreate) -> UserOut:
        """Создать нового клиента."""
        self._validate_telegram_id(user_data.telegram_id)
        user = await self.repo.create(user_data)

        dto = self._to_out(user)
        logger.info("Клиент создан: id=%s telegram_id=%s", dto.id, dto.telegram_id)
        return dto

    async def update(self, user_id: int, update_data: UserUpdate, *, strict: bool = False) -> Optional[UserOut]:
        """Обновить профиль клиента."""
        user = await self.repo.update(user_id, update_data)
        if not user:
            if strict:
                raise NotFoundError(f"Клиент не найден: id={user_id}")
            return None

        dto = self._to_out(user)
        logger.info("Профиль клиента обновлён: id=%s", dto.id)
        return dto

    async def delete(self, user_id: int, *, strict: bool = False) -> bool:
        """Удалить клиента"""
        deleted = await self.repo.delete(user_id)
        if not deleted:
            if strict:
                raise NotFoundError(f"Клиент не найден: id={user_id}")
            return False

        logger.info("Клиент удален: id=%s", user_id)
        return True

    # ──────────────────────────────────────────── write-like methods ──────────────────────────────────────────────────
    async def register_or_update_user(self, user_data: UserCreate) -> UserOut:
        """Создать клиента или обновить профиль, если клиент уже зарегистрирован."""
        self._validate_telegram_id(user_data.telegram_id)

        existing = await self.repo.get_by_telegram_id(user_data.telegram_id)
        if existing: # найден → обновляем
            logger.info("Клиент с telegram_id=%s уже существует → обновляем профиль", user_data.telegram_id)
            update_payload = user_data.model_dump(exclude={"telegram_id"}, exclude_unset=True)
            updated = await self.repo.update(existing.id, UserUpdate(**update_payload))
            if not updated:
                raise ServiceError(f"Не удалось обновить клиента id={existing.id}")

            return self._to_out(updated)

        # не найден → создаём
        created = await self.repo.create(user_data)
        if not created:
            raise ServiceError(f"Не удалось создать клиента telegram_id={user_data.telegram_id}")
        logger.info("Новый клиент создан: telegram_id=%s id=%s", created.telegram_id, created.id)

        return self._to_out(created)

    # ──────────────────────────────────────────── Admin-User logic ────────────────────────────────────────────────────
    async def ban_user(
        self,
        *,
        user_id: int,
        reason: str,
        admin_telegram_id: int,
        banned_by_admin_id: Optional[int] = None,
        strict: bool = False,
    ) -> Optional[UserOut]:
        """Заблокировать клиента с записью причины.

        `admin_telegram_id` используется для бизнес-проверок whitelist сотрудников.
        `banned_by_admin_id` — это id сотрудника из таблицы admins для audit-поля клиента.
        `admin_user_id` оставлен как устаревший compatibility-параметр для старых вызовов.
        """
        normalized_reason = self._validate_ban_reason(reason)

        user = await self.repo.get_by_id(user_id)
        if not user:
            if strict:
                raise NotFoundError(f"Клиент не найден: id={user_id}")
            return None

        if self._is_admin_telegram_id(user.telegram_id):
            raise ForbiddenError("Нельзя заблокировать сотрудника компании")

        if admin_telegram_id is not None and user.telegram_id == admin_telegram_id:
            raise ConflictError("Нельзя заблокировать самого себя")

        current_status = user.account_status
        if not can_transition(current_status, AccountStatus.BANNED):
            if strict:
                # Нельзя забанить пользователя: статус изменился или переход запрещён
                #raise ConflictError(f "Переход {current_status} -> {AccountStatus.BANNED} не разрешен.")
                raise ConflictError(f"Переход {current_status.value} -> {AccountStatus.BANNED.value} не разрешён")
            return None

        update_data = UserAdminUpdate(
            account_status=AccountStatus.BANNED,
            banned_at=datetime.now(timezone.utc),
            banned_by_admin_id = banned_by_admin_id,
            ban_reason = normalized_reason,
        )

        updated = await self.repo.update(user_id, update_data)
        if not updated:
            if strict:
                raise ConflictError("Не удалось обновить статус клиента")
            return None

        logger.info("Клиент заблокирован: id=%s admin_tg_id=%s", user_id, admin_telegram_id)
        return self._to_out(updated)

    async def unban_user(self, user_id: int, strict: bool = False) -> Optional[UserOut]:
        """Разблокировать клиента."""
        user = await self.repo.get_by_id(user_id)
        if not user:
            if strict:
                raise NotFoundError(f"Клиент не найден: id={user_id}")
            return None

        current_status = user.account_status
        if not can_transition(current_status, AccountStatus.ACTIVE):
            if strict:
                # Нельзя разбанить пользователя: статус изменился или переход запрещён
                #raise ConflictError(f "Переход {current_status} -> {AccountStatus.ACTIVE} не разрешен")
                raise ConflictError(f"Переход {current_status.value} -> {AccountStatus.ACTIVE.value} не разрешён")
            return None

        update_data = UserAdminUpdate(
            account_status=AccountStatus.ACTIVE,
            banned_at=None, # datetime.now(timezone.utc),
            banned_by_admin_id=None,
            ban_reason=None,
        )

        updated = await self.repo.update(user_id, update_data)
        if not updated:
            if strict:
                raise ConflictError("Не удалось обновить статус клиента")
            return None

        logger.info("Клиент разблокирован: id=%s", user_id)
        return self._to_out(updated)

    # ──────────────────────────────────────── Client access ───────────────────────────────────────────────────────────
    async def check_user_exists(self, telegram_id: int) -> bool:
        """Проверить, существует ли клиент с данным Telegram ID"""
        return await self.repo.exists_by_telegram_id(telegram_id)

    async def is_user_blocked(self, telegram_id: int, *, strict: bool = False) -> Optional[bool]:
        """Проверить, заблокирован ли клиент с данным Telegram ID.

        True  —  заблокирован / False — не заблокирован / None  — не найден (если strict=False)"""
        user = await self.repo.get_by_telegram_id(telegram_id)
        if not user:
            if strict:
                raise NotFoundError(f"Клиент не найден: tg_id={telegram_id}")
            return None

        return user.account_status == AccountStatus.BANNED

    # ───────────────────────────────────────── entry logic ────────────────────────────────────────────────────────────
    async def resolve_start_entry(self, telegram_id: int) -> StartEntryResult:
        """Определить, что делать, когда клиент пришёл в /start."""
        user = await self.get_by_telegram_id(telegram_id)

        if not user:
            return StartEntryResult(action=StartAction.REGISTER)

        if not can_use_bot(user.account_status): #if user.account_status != AccountStatus.ACTIVE:
            return StartEntryResult(action=StartAction.ACCESS_BLOCKED, user=user)

        if not user.phone:
            return StartEntryResult(action=StartAction.NEED_PHONE, user=user)

        return StartEntryResult(action=StartAction.MAIN_MENU, user=user)