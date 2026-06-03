from typing import Optional
from pydantic import BaseModel, Field, AwareDatetime, ConfigDict

class CategoryCreate(BaseModel):
    """Схема для создания категории/подкатегории"""
    name: str = Field(..., min_length=1, max_length=128)
    emoji: Optional[str] = Field(None, max_length=32)
    parent_id: Optional[int] = None

    sort_order: int = Field(0, ge=0)
    is_active: bool = True
    slug: Optional[str] = Field(None, max_length=128)


class CategoryUpdate(BaseModel):
    """Схема для обновления категории/подкатегории"""
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    emoji: Optional[str] = Field(None, max_length=32)

    # нужен тут?
    parent_id: Optional[int] = None

    sort_order: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None
    slug: Optional[str] = Field(None, max_length=128)


class CategoryOut(BaseModel):
    """Схема для возврата данных о категории наружу"""
    id: int
    name: str
    emoji: Optional[str] = None
    parent_id: Optional[int] = None

    sort_order: int
    is_active: bool
    slug: Optional[str] = None

    created_at: AwareDatetime
    updated_at: AwareDatetime

    model_config = ConfigDict(from_attributes=True)