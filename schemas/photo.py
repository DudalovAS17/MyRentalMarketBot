from typing import Optional
from pydantic import BaseModel, Field, AwareDatetime, ConfigDict


class PhotoCreate(BaseModel):
    """Схема для создания фотографии товара каталога."""

    item_id: int
    telegram_file_id: Optional[str] = Field(None, max_length=500)
    url: Optional[str] = Field(None, max_length=1000)
    sort_order: int = Field(0, ge=0)
    is_main: bool = False


class PhotoUpdate(BaseModel):
    """Схема для обновления фотографии товара каталога."""

    telegram_file_id: Optional[str] = Field(None, max_length=500)
    url: Optional[str] = Field(None, max_length=1000)
    sort_order: Optional[int] = Field(None, ge=0)
    is_main: Optional[bool] = None


class PhotoOut(BaseModel):
    """Схема для возврата данных о фотографии товара наружу."""

    id: int
    item_id: int

    telegram_file_id: Optional[str] = None
    url: Optional[str] = None
    sort_order: int
    is_main: bool

    created_at: AwareDatetime
    updated_at: AwareDatetime

    model_config = ConfigDict(from_attributes=True)