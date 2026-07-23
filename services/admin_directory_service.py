import logging
from typing import Optional

from db.repositories.admin import AdminRepository
from schemas.admin import AdminCreate, AdminOut
from status.user_status import AccountStatus
from utils.errors import ForbiddenError, NotFoundError

logger = logging.getLogger(__name__)


class AdminDirectoryService:
    """Сервис для чтения профилей администраторов/менеджеров."""

    def __init__(self, repo: AdminRepository) -> None:
        self.repo = repo

    @staticmethod
    def _to_out(admin) -> AdminOut:
        return AdminOut.model_validate(admin)

    # ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    async def get_by_id(self, admin_id: int, *, strict: bool = False) -> Optional[AdminOut]:
        """Вернуть администратора/менеджера по ID."""
        admin = await self.repo.get_by_id(admin_id)
        if not admin:
            if strict:
                raise NotFoundError(f"Сотрудник не найден: id={admin_id}")
            return None

        return self._to_out(admin)

    async def get_by_telegram_id(self, telegram_id: int, *, strict: bool = False) -> Optional[AdminOut]:
        """Вернуть администратора/менеджера по Telegram ID."""
        admin = await self.repo.get_by_telegram_id(telegram_id)
        if not admin:
            if strict:
                raise NotFoundError(f"Сотрудник не найден: tg_id={telegram_id}")
            return None

        return self._to_out(admin)

    async def ensure_active_admin_by_id(self, admin_id: int) -> AdminOut:
        """Вернуть активного сотрудника ID или запретить действие."""
        admin = await self.get_by_id(admin_id, strict=True)
        if not admin.is_active or admin.account_status != AccountStatus.ACTIVE:
            raise ForbiddenError("Доступ сотрудника отключён")
        return admin

    async def ensure_active_admin_by_telegram_id(self, telegram_id: int) -> AdminOut:
        """Вернуть активного сотрудника или запретить админское действие."""
        admin = await self.get_by_telegram_id(telegram_id, strict=True)
        if not admin.is_active or admin.account_status != AccountStatus.ACTIVE:
            raise ForbiddenError("Доступ сотрудника отключён")
        return admin

    async def sync_admins_from_settings(self, admin_ids: set[int]) -> None:
        """Idempotently create admin profiles for Telegram IDs from settings.

        ADMIN_IDS remains the source of truth for access control; this sync only
        guarantees that domain FK/audit fields can resolve an internal admins.id.
        """
        if not admin_ids:
            logger.warning("ADMIN_IDS is empty — no admin profiles to bootstrap")
            return

        created_count = 0
        for telegram_id in sorted(admin_ids):
            existing = await self.repo.get_by_telegram_id(telegram_id)
            if existing:
                continue

            await self.repo.create(AdminCreate(telegram_id=telegram_id))
            created_count += 1
            logger.info("Bootstrapped admin profile from ADMIN_IDS: telegram_id=%s", telegram_id)

        logger.info(
            "Admin bootstrap sync completed: configured=%s created=%s existing=%s",
            len(admin_ids),
            created_count,
            len(admin_ids) - created_count,
        )
