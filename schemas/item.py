from pydantic import BaseModel, Field, AwareDatetime, ConfigDict, field_validator
from typing import Optional, Dict, Any
from decimal import Decimal

from status.item_status import ItemStatus


class ItemCreate(BaseModel):
    """Схема для создания объявления"""

    category_id: int
    subcategory_id: Optional[int] = None
    title: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = None
    price: Decimal = Field(..., ge=0)
    deposit: Optional[Decimal] = Field(None, ge=0)
    min_rental_period: int = Field(1, ge=1)
    max_rental_period: Optional[int] = None
    location: Optional[str] = None
    coordinates: Optional[Dict[str, Any]] = None

    @field_validator("coordinates")
    @classmethod
    def validate_coordinates(cls, v):
        if v is not None:
            if "lat" not in v or "lng" not in v:
                raise ValueError("coordinates must have 'lat' and 'lng'")
        return v


class ItemUpdate(BaseModel):
    """Схема для обновления объявления (только изменяемые поля)"""

    category_id: Optional[int] = None
    subcategory_id: Optional[int] = None
    title: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = None
    price: Optional[Decimal] = Field(None, ge=0)
    deposit: Optional[Decimal] = Field(None, ge=0)
    min_rental_period: Optional[int] = Field(None, ge=1)
    max_rental_period: Optional[int] = None
    location: Optional[str] = None
    coordinates: Optional[Dict[str, Any]] = None


class ItemOut(BaseModel):
    """Схема для возврата данных об объявлении"""

    id: int
    user_id: int
    category_id: int
    subcategory_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    price: Decimal = Field(..., ge=0)
    deposit: Optional[Decimal] = None
    location: Optional[str] = None
    coordinates: Optional[Dict[str, Any]] = None
    min_rental_period: int
    max_rental_period: Optional[int] = None
    status: ItemStatus
    views_count: int
    orders_count: int

    moderated_at: Optional[AwareDatetime] = None
    moderated_by_admin_id: Optional[int] = None
    moderation_reason: Optional[str] = None

    created_at: AwareDatetime
    updated_at: AwareDatetime

    model_config = ConfigDict(from_attributes=True)


class ItemModerationUpdate(BaseModel):
    """Для Админов - схема для обновления объявления"""

    is_featured: Optional[bool] = None
    status: Optional[ItemStatus] = None
    moderation_reason: Optional[str] = None


class ItemAdminOut(ItemOut): #
    """Админская схема для возврата данных об объявлении"""

    is_featured: Optional[bool] = None
    moderated_at: Optional[AwareDatetime] = None
    moderated_by_admin_id: Optional[int] = None
    moderation_reason: Optional[str] = None


class ItemCreateDraft(BaseModel):
    """ Черновик для FSM (пошаговое заполнение).

    Поля и названия 1-в-1 совпадают с ItemCreate, но почти всё Optional, чтобы заполнять по шагам.
    """

    model_config = ConfigDict(extra="forbid")  # 🚫 запрет лишних полей

    category_id: Optional[int] = None
    subcategory_id: Optional[int] = None

    title: Optional[str] = Field(default=None, min_length=3, max_length=255)
    description: Optional[str] = None

    price: Optional[Decimal] = Field(default=None, ge=0)
    deposit: Optional[Decimal] = Field(default=None, ge=0)

    min_rental_period: int = Field(default=1, ge=1)
    max_rental_period: Optional[int] = None

    location: Optional[str] = None
    coordinates: Optional[Dict[str, Any]] = None