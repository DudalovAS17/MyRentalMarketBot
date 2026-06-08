from typing import Optional
from sqlalchemy import exists, select

from db.models.admin_actions import AdminAction
from db.models.admins import Admin
from db.repositories.base import BaseRepository
from schemas.admin import AdminCreate, AdminUpdate
from status.admin_status import AdminRole
from status.user_status import AccountStatus


class AdminRepository(BaseRepository):
    """Репозиторий администраторов и менеджеров компании."""

    # ───────────────────────────────────────────────────────────────────────────────────────────────────────
    @staticmethod
    def _apply_id_order(stmt):
        """Стабильный порядок выдачи сотрудников."""
        return stmt.order_by(Admin.id.asc())

    @staticmethod
    def _apply_pagination(stmt, *, limit: Optional[int], offset: int):
        if limit is not None:
            stmt = stmt.limit(limit).offset(offset)
        return stmt

    @staticmethod
    def _apply_role_filter(stmt, role: AdminRole):
        """Оставить только сотрудников с указанной ролью."""
        return stmt.where(Admin.role == role)

    @staticmethod
    def _apply_account_status_filter(stmt, status: AccountStatus):
        """Оставить только сотрудников с указанным статусом аккаунта."""
        return stmt.where(Admin.account_status == status)

    @staticmethod
    def _apply_active_filter(stmt):
        """Оставить только сотрудников с включённым доступом к админке."""
        return stmt.where(Admin.is_active.is_(True))

    # ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    async def list_all(self, *, active_only: bool = False, limit: Optional[int] = None, offset: int = 0) -> list[Admin]:
        """Вернуть список администраторов и менеджеров компании."""
        async with self._session() as s:
            stmt = select(Admin)
            if active_only:
                stmt = self._apply_active_filter(stmt)
            stmt = self._apply_id_order(stmt)
            stmt = self._apply_pagination(stmt, limit=limit, offset=offset)

            return await self._list(s, stmt)

    async def list_by_role(self, role: AdminRole,
        *, active_only: bool = False, limit: Optional[int] = None, offset: int = 0) -> list[Admin]:
        """Вернуть сотрудников с указанной ролью."""
        async with self._session() as s:
            stmt = select(Admin)
            stmt = self._apply_role_filter(stmt, role)
            if active_only:
                stmt = self._apply_active_filter(stmt)
            stmt = self._apply_id_order(stmt)
            stmt = self._apply_pagination(stmt, limit=limit, offset=offset)

            return await self._list(s, stmt)

    async def list_by_account_status(self, status: AccountStatus,
        *, limit: Optional[int] = None, offset: int = 0) -> list[Admin]:
        """Вернуть сотрудников с указанным статусом аккаунта."""
        async with self._session() as s:
            stmt = select(Admin)
            stmt = self._apply_account_status_filter(stmt, status)
            stmt = self._apply_id_order(stmt)
            stmt = self._apply_pagination(stmt, limit=limit, offset=offset)

            return await self._list(s, stmt)

    async def get_by_id(self, admin_id: int) -> Optional[Admin]:
        """Найти сотрудника по ID."""
        async with self._session() as s:
            return await s.get(Admin, admin_id)

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[Admin]:
        """Найти сотрудника по Telegram ID."""
        async with self._session() as s:
            stmt = select(Admin).where(Admin.telegram_id == telegram_id)
            return await self._one_or_none(s, stmt)

    async def exists_by_telegram_id(self, telegram_id: int) -> bool:
        """Проверить существование сотрудника по Telegram ID."""
        async with self._session() as s:
            stmt = select(exists().where(Admin.telegram_id == telegram_id))
            return await self._exists(s, stmt)

    # ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    async def create(self, admin_data: AdminCreate) -> Admin:
        """Создать администратора или менеджера компании."""
        async with self._session() as s:
            obj = Admin(**admin_data.model_dump()) # exclude_none=True
            return await self._add_commit_refresh(s, obj)

    async def update(self, admin_id: int, update_data: AdminUpdate) -> Optional[Admin]:
        """Обновить данные администратора или менеджера компании."""
        async with self._session() as s:
            obj: Optional[Admin] = await s.get(Admin, admin_id)
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

    async def delete(self, admin_id: int) -> bool:
        """Удалить администратора или менеджера компании."""
        async with self._session() as s:
            obj = await s.get(Admin, admin_id)
            if not obj:
                return False

            return await self._delete_commit(s, obj)


class AdminActionRepository(BaseRepository):
    """Репозиторий журнала действий администратора"""

    # ───────────────────────────────────────────────────────────────────────────────────────────────────────
    @staticmethod
    def _apply_recent_order(stmt):
        """Стабильный порядок выдачи audit-записей: новые сначала."""
        return stmt.order_by(AdminAction.created_at.desc(), AdminAction.id.desc())

    @staticmethod
    def _apply_pagination(stmt, *, limit: Optional[int], offset: int):
        if limit is not None:
            stmt = stmt.limit(limit).offset(offset)
        return stmt

    @staticmethod
    def _apply_admin_id_filter(stmt, admin_id: int):
        """Оставить audit-записи внутреннего администратора."""
        return stmt.where(AdminAction.admin_id == admin_id)

    @staticmethod
    def _apply_admin_tg_id_filter(stmt, admin_tg_id: int):
        """Оставить audit-записи администратора по Telegram ID."""
        return stmt.where(AdminAction.admin_tg_id == admin_tg_id)

    @staticmethod
    def _apply_entity_filter(stmt, *, entity_type: str, entity_id: str):
        """Оставить audit-записи по сущности."""
        return stmt.where(
            AdminAction.entity_type == entity_type,
            AdminAction.entity_id == entity_id,
        )

    @staticmethod
    def _apply_action_type_filter(stmt, action_type: str):
        """Оставить audit-записи указанного типа действия."""
        return stmt.where(AdminAction.action_type == action_type)

    # ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    async def list_recent(self, *, limit: Optional[int] = None, offset: int = 0) -> list[AdminAction]:
        """Вернуть последние audit-записи."""
        async with self._session() as s:
            stmt = select(AdminAction)
            stmt = self._apply_recent_order(stmt)
            stmt = self._apply_pagination(stmt, limit=limit, offset=offset)
            return await self._list(s, stmt)

    async def list_by_admin_id(self, admin_id: int, *, limit: Optional[int] = None, offset: int = 0) -> list[AdminAction]:
        """Вернуть audit-записи внутреннего администратора."""
        async with self._session() as s:
            stmt = select(AdminAction)
            stmt = self._apply_admin_id_filter(stmt, admin_id)
            stmt = self._apply_recent_order(stmt)
            stmt = self._apply_pagination(stmt, limit=limit, offset=offset)
            return await self._list(s, stmt)

    async def list_by_admin_tg_id(self, admin_tg_id: int, *, limit: Optional[int] = None, offset: int = 0) -> list[AdminAction]:
        """Вернуть audit-записи администратора по Telegram ID."""
        async with self._session() as s:
            stmt = select(AdminAction)
            stmt = self._apply_admin_tg_id_filter(stmt, admin_tg_id)
            stmt = self._apply_recent_order(stmt)
            stmt = self._apply_pagination(stmt, limit=limit, offset=offset)

            return await self._list(s, stmt)

    async def list_by_entity(self,
            *, entity_type: str, entity_id: str | int, limit: Optional[int] = None, offset: int = 0) -> list[AdminAction]:
        """Вернуть audit-записи по сущности."""
        async with self._session() as s:
            stmt = select(AdminAction)
            stmt = self._apply_entity_filter(stmt, entity_type=entity_type, entity_id=str(entity_id))
            stmt = self._apply_recent_order(stmt)
            stmt = self._apply_pagination(stmt, limit=limit, offset=offset)
            return await self._list(s, stmt)

    async def list_by_action_type(self, action_type: str,
            *, limit: Optional[int] = None, offset: int = 0) -> list[AdminAction]:
        """Вернуть audit-записи указанного типа действия."""
        async with self._session() as s:
            stmt = select(AdminAction)
            stmt = self._apply_action_type_filter(stmt, action_type)
            stmt = self._apply_recent_order(stmt)
            stmt = self._apply_pagination(stmt, limit=limit, offset=offset)
            return await self._list(s, stmt)

    async def get_by_id(self, action_id: int) -> Optional[AdminAction]:
        """Найти audit-запись по ID."""
        async with self._session() as s:
            return await s.get(AdminAction, action_id)

    # ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    async def create(self,
        *, admin_tg_id: int, action_type: str, entity_type: str, entity_id: str,
        admin_id: Optional[int] = None, note: str | None = None, payload: dict[str, object] | None = None,
    ) -> AdminAction:
        """Создать запись о действии администратора"""
        async with self._session() as s:
            obj = AdminAction(
                admin_id=admin_id,
                admin_tg_id=admin_tg_id,
                action_type=action_type,
                entity_type=entity_type,
                entity_id=entity_id,
                note=note,
                payload=payload,
            )
            return await self._add_commit_refresh(s, obj)