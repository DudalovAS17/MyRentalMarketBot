from pydantic import BaseModel, Field
from typing import Optional


class PhotoBase(BaseModel):
    """Базовая схема — общие поля."""
    item_id: int = Field(..., description="ID объявления, к которому относится фото")
    telegram_file_id: str = Field(..., max_length=500)
    order: Optional[int] = Field(None, description="Порядок отображения фото")

    class Config:
        from_attributes = True  # Позволяет создавать модель из ORM-объекта


class PhotoCreate(PhotoBase):
    """Используется при создании фото.
    order может быть не указан — тогда сервис сам подставит следующий.
    """
    pass


class PhotoUpdate(BaseModel):
    """Частичное обновление фото"""
    telegram_file_id: Optional[str] = None
    order: Optional[int] = None

    class Config:
        from_attributes = True


class PhotoOut(PhotoBase):
    """То, что возвращается наружу — полностью описывает фото"""
    id: int

    class Config:
        from_attributes = True

