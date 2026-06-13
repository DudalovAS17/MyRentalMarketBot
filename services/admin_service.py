import enum
from typing import Optional

from db.repositories.admin import AdminActionRepository
from schemas.admin import AdminActionOut
from utils.errors import ValidationError

class AdminActionService:
    """Сервис для записи и чтения audit-действий сотрудников компании."""

    def __init__(self, repo: AdminActionRepository) -> None:
        self.repo = repo

    # ────────────────────────────────────────── DTO helpers ───────────────────────────────────────────────────────────
    @staticmethod
    def _to_out(action) -> AdminActionOut:
        return AdminActionOut.model_validate(action)

    @classmethod
    def _to_out_list(cls, actions) -> list[AdminActionOut]:
        return [cls._to_out(action) for action in actions]

    # ─────────────────────────────────────── Business validation ──────────────────────────────────────────────────────
    @staticmethod
    def _enum_to_str(value: str | enum.Enum) -> str:
        return value.value if isinstance(value, enum.Enum) else str(value)

    @staticmethod
    def _validate_admin_tg_id(admin_tg_id: int) -> None:
        if admin_tg_id <= 0:
            raise ValidationError("Некорректный Telegram ID сотрудника")

    @staticmethod
    def _validate_admin_id(admin_id: int) -> None:
        if admin_id <= 0:
            raise ValidationError("Некорректный ID сотрудника")

    @staticmethod
    def _validate_required_text(value: str, field_name: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValidationError(f"{field_name} не может быть пустым")
        return normalized

    # ────────────────────────────────────────── Read methods ──────────────────────────────────────────────────────────
    async def list_recent(self, *, limit: Optional[int] = None, offset: int = 0) -> list[AdminActionOut]:
        """Вернуть последние audit-записи."""
        actions = await self.repo.list_recent(limit=limit, offset=offset)
        return self._to_out_list(actions)

    async def list_by_admin_tg_id(self, admin_tg_id: int,
                                  *, limit: Optional[int] = None, offset: int = 0) -> list[AdminActionOut]:
        """Вернуть audit-записи сотрудника по Telegram ID."""
        self._validate_admin_tg_id(admin_tg_id)
        actions = await self.repo.list_by_admin_tg_id(admin_tg_id, limit=limit, offset=offset)
        return self._to_out_list(actions)

    async def list_by_admin_id(self, admin_id: int, *, limit: Optional[int] = None, offset: int = 0) -> list[AdminActionOut]:
        """Вернуть audit-записи сотрудника по ID."""
        self._validate_admin_id(admin_id)
        actions = await self.repo.list_by_admin_id(admin_id, limit=limit, offset=offset)
        return self._to_out_list(actions)

    async def list_by_entity(
        self,
        *,
        entity_type: str | enum.Enum,
        entity_id: str | int,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> list[AdminActionOut]:
        """Вернуть audit-записи по сущности."""
        entity_type_str = self._validate_required_text(self._enum_to_str(entity_type), "entity_type")
        entity_id_str = self._validate_required_text(str(entity_id), "entity_id")
        actions = await self.repo.list_by_entity(
            entity_type=entity_type_str,
            entity_id=entity_id_str,
            limit=limit,
            offset=offset,
        )
        return self._to_out_list(actions)

    # ─────────────────────────────────────────── write methods ────────────────────────────────────────────────────────
    async def log_action(
        self,
        *,
        admin_tg_id: int,
        action_type: str | enum.Enum,
        entity_type: str | enum.Enum,
        entity_id: str | int,
        admin_id: Optional[int] = None,
        note: Optional[str] = None,
        payload: dict[str, object] | None = None
    ) -> AdminActionOut:
        """Записать действие сотрудника и вернуть DTO созданной audit-записи."""
        self._validate_admin_tg_id(admin_tg_id)

        # приведем к строкам
        action_type_str = self._validate_required_text(self._enum_to_str(action_type), "action_type")
        entity_type_str = self._validate_required_text(self._enum_to_str(entity_type), "entity_type")
        entity_id_str = self._validate_required_text(str(entity_id), "entity_id")

        obj =  await self.repo.create(
            admin_tg_id=admin_tg_id,
            action_type=action_type_str,
            entity_type=entity_type_str,
            entity_id=entity_id_str,
            admin_id=admin_id,
            note=note,
            payload=payload
        )

        return self._to_out(obj)