from typing import Optional
from decimal import Decimal
from pydantic import BaseModel, AwareDatetime, ConfigDict

from status.user_status import AccountStatus

class UserCreate(BaseModel):
    """Схема для создания пользователя"""

    telegram_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None


class UserUpdate(BaseModel):
    """Схема для обновления пользователя"""

    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None


class UserOut(BaseModel):
    """Схема для возврата данных о пользователе наружу"""

    id: int
    telegram_id: int

    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None

    rating: Decimal
    rating_count: int

    account_status: AccountStatus

    banned_at: Optional[AwareDatetime] = None
    banned_by_admin_id: Optional[int] = None
    ban_reason: Optional[str] = None

    created_at: AwareDatetime
    updated_at: AwareDatetime

    model_config = ConfigDict(from_attributes=True)


class UserAdminUpdate(BaseModel):
    """Схема для админского обновления пользователя"""

    account_status: Optional[AccountStatus] = None

    banned_at: Optional[AwareDatetime] = None
    banned_by_admin_id: Optional[int] = None
    ban_reason: Optional[str] = None
