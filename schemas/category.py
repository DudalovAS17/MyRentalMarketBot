from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class CategoryOut(BaseModel):
    """Схема для возврата данных о категории наружу"""
    id: int
    name: str
    emoji: Optional[str] = None
    parent_id: Optional[int] = None
    #created_at: Optional[datetime] = None
    #updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True  # Позволяет валидировать прямо из SQLAlchemy-модели
