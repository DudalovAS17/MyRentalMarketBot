from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from decimal import Decimal
from datetime import datetime

class ItemCreate(BaseModel):
    """Схема для создания объявления"""
    user_id: int
    category_id: int # Optional[int] = None
    subcategory_id: Optional[int] = None
    title: str = Field(..., min_length=3, max_length=255) # Optional[str] = None
    description: Optional[str] = None
    price: Decimal = Field(..., ge=0) # цена ≥ 0   # Optional[Decimal] = None
    deposit: Optional[Decimal] = Field(None, ge=0) # залог ≥ 0
    min_rental_period: int = Field(1, ge=1)  # минимум 1 день    # Optional[int] = None
    max_rental_period: Optional[int] = None
    location: Optional[str] = None
    coordinates: Optional[Dict[str, Any]] = None
    is_available: bool = True
    is_featured: bool = False
    #photos: Optional[List[str]] = None  # ссылки на фото

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
    is_available: Optional[bool] = None
    is_featured: Optional[bool] = None

class ItemOut(BaseModel):
    """Схема для возврата данных об объявлении"""
    id: int
    user_id: int
    category_id: Optional[int] = None
    subcategory_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    price: float = Field(..., ge=0)
    deposit: Optional[float] = None
    location: Optional[str] = None
    min_rental_period: Optional[int] = None
    max_rental_period: Optional[int] = None
    is_available: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True  # позволяет строить схему из SQLAlchemy-модели


