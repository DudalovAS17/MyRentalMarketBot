from pydantic import BaseModel, Field, AwareDatetime, ConfigDict, field_validator
from typing import Optional, Dict, Any
from decimal import Decimal

from status.item_status import ItemStatus

# ────────────────────────────────────────── Item  ─────────────────────────────────────────────────────────────────────
class ItemCreate(BaseModel):
    """Схема для создания товара каталога."""
    category_id: int
    subcategory_id: Optional[int] = None

    title: str = Field(..., min_length=3, max_length=200)
    description: Optional[str] = None
    short_description: Optional[str] = Field(None, max_length=300)

    price: Decimal = Field(..., ge=0)
    price_text: Optional[str] = Field(None, max_length=100)

    available_quantity: int = Field(None, ge=0)

    is_featured: bool = False
    sort_order: int = Field(None, ge=0)

    min_rental_period: int = Field(None, ge=1)
    max_rental_period: Optional[int] = Field(None, ge=1)


class ItemUpdate(BaseModel):
    """Схема для обновления товара каталога. (только изменяемые поля)"""
    category_id: Optional[int] = None
    subcategory_id: Optional[int] = None

    title: Optional[str] = Field(None, min_length=3, max_length=200)
    description: Optional[str] = None
    short_description: Optional[str] = Field(None, max_length=300)

    price: Optional[Decimal] = Field(None, ge=0)
    price_text: Optional[str] = Field(None, max_length=100)

    available_quantity: Optional[int] = Field(None, ge=0)

    is_featured: Optional[bool] = None
    sort_order: Optional[int] = Field(None, ge=0)

    min_rental_period: Optional[int] = Field(None, ge=1)
    max_rental_period: Optional[int] = Field(None, ge=1)


class ItemOut(BaseModel):
    """Схема для возврата данных товара каталога."""
    id: int
    category_id: int
    subcategory_id: Optional[int] = None

    title: str
    description: Optional[str] = None
    short_description: Optional[str] = None

    price: Decimal = Field(..., ge=0)
    price_text: Optional[str] = None

    available_quantity: int

    is_featured: bool
    sort_order: int

    min_rental_period: int
    max_rental_period: Optional[int] = None

    status: ItemStatus

    views_count: int
    orders_count: int

    created_at: AwareDatetime
    updated_at: AwareDatetime

    model_config = ConfigDict(from_attributes=True)


# ────────────────────────────────────────── Item Characteristic ───────────────────────────────────────────────────────
class ItemCharacteristicCreate(BaseModel):
    """Схема для создания характеристики товара каталога."""

    item_id: int
    name: str = Field(..., min_length=1, max_length=100)
    value: str = Field(..., min_length=1, max_length=200)
    sort_order: int = Field(0, ge=0)


class ItemCharacteristicUpdate(BaseModel):
    """Схема для обновления характеристики товара каталога."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    value: Optional[str] = Field(None, min_length=1, max_length=200)
    sort_order: Optional[int] = Field(None, ge=0)


class ItemCharacteristicOut(BaseModel):
    """Схема для возврата характеристики товара каталога."""

    id: int
    item_id: int
    name: str
    value: str
    sort_order: int

    created_at: AwareDatetime
    updated_at: AwareDatetime

    model_config = ConfigDict(from_attributes=True)


# ────────────────────────────────────────── Item Moderation ───────────────────────────────────────────────────────────
class ItemModerationUpdate(BaseModel):
    """Для Админов - схема для публикации/скрытия товара каталога."""

    is_featured: Optional[bool] = None
    status: Optional[ItemStatus] = None


class ItemAdminOut(ItemOut):
    """Админская схема для возврата товара каталога."""

    created_by_admin_id: Optional[int] = None
    updated_by_admin_id: Optional[int] = None

    moderated_at: Optional[AwareDatetime] = None


# ────────────────────────────────────────── Item Draft ────────────────────────────────────────────────────────────────
class ItemCreateDraft(BaseModel):
    """ Черновик для FSM (пошаговое заполнение).

    Поля и названия 1-в-1 совпадают с ItemCreate, но почти всё Optional, чтобы заполнять по шагам.
    """

    model_config = ConfigDict(extra="forbid")  # 🚫 запрет лишних полей

    category_id: Optional[int] = None
    subcategory_id: Optional[int] = None

    title: Optional[str] = Field(default=None, min_length=3, max_length=200)
    description: Optional[str] = None
    short_description: Optional[str] = Field(None, max_length=300)

    price: Optional[Decimal] = Field(default=None, ge=0)
    price_text: Optional[str] = Field(None, max_length=100)

    available_quantity: int = Field(1, ge=0)

    min_rental_period: int = Field(default=1, ge=1)
    #min_rental_period: Optional[int] = Field(None, ge=1)
    max_rental_period: Optional[int] = Field(None, ge=1)

    is_featured: bool = False
    sort_order: int = Field(0, ge=0)