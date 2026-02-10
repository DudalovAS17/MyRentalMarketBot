from pydantic import BaseModel, Field, AwareDatetime, ConfigDict
from typing import Optional

class CategoryCreate(BaseModel):
    """Схема для создания категории/подкатегории"""
    name: str = Field(..., min_length=1, max_length=128)
    emoji: Optional[str] = Field(None, max_length=32)
    parent_id: Optional[int] = None


class CategoryUpdate(BaseModel):
    """Схема для обновления категории/подкатегории"""
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    emoji: Optional[str] = Field(None, max_length=32)
    parent_id: Optional[int] = None

class CategoryOut(BaseModel):
    """Схема для возврата данных о категории наружу"""
    id: int
    name: str
    emoji: Optional[str] = None
    parent_id: Optional[int] = None
    created_at: AwareDatetime #Optional[datetime] = None
    updated_at: AwareDatetime # Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
