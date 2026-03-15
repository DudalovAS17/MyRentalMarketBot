from typing import Optional
from pydantic import BaseModel, Field, AwareDatetime, ConfigDict


class PhotoCreate(BaseModel):
    """Схема для создания фото."""

    #item_id: int = Field(..., description="ID объявления, к которому относится фото") # приходит из контекста
    telegram_file_id: str = Field(..., max_length=500)

    # order может быть не указан — тогда сервис сам подставит следующий
    order: Optional[int] = Field(None, ge=0, description="Порядок отображения фото")
    # если порядок всегда задаётся входом
    #order: int = Field(0, ge=0, description="Порядок отображения фото")


class PhotoUpdate(BaseModel):
    """Частичное обновление фото"""

    telegram_file_id: Optional[str] = Field(None, max_length=500)
    order: Optional[int] = Field(None, ge=0)


class PhotoOut(BaseModel):
    """Схема для возврата данных о фото наружу."""

    id: int
    item_id: int
    telegram_file_id: str
    order: int # = Field(..., ge=0)

    created_at: AwareDatetime
    updated_at: AwareDatetime

    model_config = ConfigDict(from_attributes=True)