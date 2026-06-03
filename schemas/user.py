from typing import Optional
from pydantic import BaseModel, AwareDatetime, ConfigDict, Field

from status.user_status import AccountStatus

class UserCreate(BaseModel):
    """Схема для создания клиента."""

    telegram_id: int

    username: Optional[str] = Field(None, max_length=100)
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    full_name: Optional[str] = Field(None, max_length=200)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=100)
    language_code: Optional[str] = Field(None, max_length=10)


class UserUpdate(BaseModel):
    """Схема для обновления профиля клиента."""

    username: Optional[str] = Field(None, max_length=100)
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    full_name: Optional[str] = Field(None, max_length=200)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=100)
    language_code: Optional[str] = Field(None, max_length=10)


class UserOut(BaseModel):
    """Схема для возврата данных клиента наружу."""

    id: int
    telegram_id: int

    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    language_code: Optional[str] = None

    account_status: AccountStatus

    banned_at: Optional[AwareDatetime] = None
    banned_by_admin_id: Optional[int] = None
    ban_reason: Optional[str] = None

    created_at: AwareDatetime
    updated_at: AwareDatetime

    model_config = ConfigDict(from_attributes=True)


# ────────────────────────────────────────── User Moderation ───────────────────────────────────────────────────────────
class UserAdminUpdate(BaseModel):
    """Схема для админского обновления статуса клиента."""

    account_status: Optional[AccountStatus] = None

    banned_at: Optional[AwareDatetime] = None
    banned_by_admin_id: Optional[int] = None
    ban_reason: Optional[str] = None