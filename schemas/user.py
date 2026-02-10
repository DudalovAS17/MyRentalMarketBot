from pydantic import BaseModel, Field, AwareDatetime, ConfigDict
from typing import Optional

from db.models.user import AccountStatus

class UserCreate(BaseModel):
    """Схема для создания пользователя"""

    telegram_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None

    # устанавливаются автоматически сервисом/БД
    #rating: float = Field(0.0, ge=0, le=5) # float = 0.0
    #rating_count: int = Field(0, ge=0) # int = 0
    #is_blocked: bool = False
    #account_status: str = "ACTIVE"

    # бан-поля — строго админские
    #banned_at: Optional[datetime] = None
    #banned_by_admin_id: Optional[int] = None
    #ban_reason: Optional[str] = None


class UserUpdate(BaseModel):
    """Схема для обновления пользователя"""

    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None


class UserAdminUpdate(BaseModel):
    """Схема для админского обновления пользователя"""

    is_admin: Optional[bool] = None
    is_blocked: Optional[bool] = None
    account_status: Optional[AccountStatus] = None

    # аудит бана
    banned_at: Optional[AwareDatetime] = None
    banned_by_admin_id: Optional[int] = None
    ban_reason: Optional[str] = None

    # рейтинг (если у вас это админская/системная зона)
    rating: Optional[float] = Field(None, ge=0, le=5)
    rating_count: Optional[int] = Field(None, ge=0)

# Если рейтинг считается автоматически из Review — то лучше вообще убрать rating/rating_count из любых Update-схем
# и менять только сервисом.


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

    # В Out дефолты не вредят, но чаще делают просто типы (без = False)
    rating: float # = Field(0.0, ge=0, le=5)
    rating_count: int # = Field(0, ge=0) # = 0
    is_blocked: bool # = False
    is_admin: bool # = False
    account_status: AccountStatus # = AccountStatus.ACTIVE

    banned_at: Optional[AwareDatetime] = None
    banned_by_admin_id: Optional[int] = None
    ban_reason: Optional[str] = None

    created_at: AwareDatetime
    updated_at: AwareDatetime

    model_config = ConfigDict(from_attributes=True)

