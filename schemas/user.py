from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class UserCreate(BaseModel):
    """Схема для создания пользователя"""
    telegram_id: str
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    rating: float = 0.0
    rating_count: int = 0
    is_blocked: bool = False


class UserUpdate(BaseModel):
    """Схема для обновления пользователя"""
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    rating: Optional[float] = None
    rating_count: Optional[int] = None
    is_blocked: Optional[bool] = None

class UserOut(BaseModel):
    """Схема для возврата данных о пользователе наружу"""
    id: int
    telegram_id: str
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    rating: float = Field(0, ge=0, le=5)
    rating_count: int = 0
    is_blocked: bool = False
    is_admin: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True  # ← позволяет валидировать прямо из SQLAlchemy-модели
