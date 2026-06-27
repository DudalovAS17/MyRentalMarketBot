from typing import Optional
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from status.admin_status import AdminActionType, AdminEntityType, AdminRole
from status.user_status import AccountStatus


class AdminCreate(BaseModel):
    """Схема для создания менеджера/сотрудника компании."""

    telegram_id: int
    username: Optional[str] = Field(default=None, max_length=100)
    full_name: Optional[str] = Field(default=None, max_length=200)
    phone: Optional[str] = Field(default=None, max_length=20)
    role: AdminRole = AdminRole.MANAGER # ?
    is_active: bool = True
    account_status: AccountStatus = AccountStatus.ACTIVE # ?


class AdminUpdate(BaseModel):
    """Схема для обновления менеджера/сотрудника компании."""

    username: Optional[str] = Field(default=None, max_length=100)
    full_name: Optional[str] = Field(default=None, max_length=200)
    phone: Optional[str] = Field(default=None, max_length=20)
    role: Optional[AdminRole] = None
    is_active: Optional[bool] = None
    account_status: Optional[AccountStatus] = None


class AdminOut(BaseModel):
    """Схема для возврата данных менеджера/сотрудника компании."""

    id: int
    telegram_id: int
    username: Optional[str] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    role: AdminRole
    is_active: bool
    account_status: AccountStatus
    created_at: AwareDatetime
    updated_at: AwareDatetime

    model_config = ConfigDict(from_attributes=True)


# ──────────────────────────────────────────── Admin Action ────────────────────────────────────────────────────────────
class AdminActionCreate(BaseModel):
    """Схема для записи audit-действия админа (создание)"""

    admin_id: Optional[int] = None
    admin_tg_id: int

    action_type: str = Field(..., min_length=1, max_length=64)
    entity_type: str = Field(..., min_length=1, max_length=32)
    entity_id: str = Field(..., min_length=1, max_length=64)

    note: Optional[str] = Field(None, max_length=255)
    payload: Optional[dict[str, object]] = None


class AdminActionOut(BaseModel):
    """Схема для возврата audit-записи наружу"""

    id: int
    admin_id: Optional[int] = None
    admin_tg_id: int

    action_type: str = Field(..., min_length=1, max_length=64)
    entity_type: str = Field(..., min_length=1, max_length=32)
    entity_id: str = Field(..., min_length=1, max_length=64)

    note: Optional[str] = None
    payload: Optional[dict[str, object]] = None

    created_at: AwareDatetime
    updated_at: AwareDatetime

    model_config = ConfigDict(from_attributes=True)