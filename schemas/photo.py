from pydantic import BaseModel, Field, AwareDatetime, ConfigDict


class PhotoCreate(BaseModel):
    """Схема для создания фото"""

    telegram_file_id: str = Field(..., max_length=500)


class PhotoOut(BaseModel):
    """Схема для возврата данных о фото наружу"""

    id: int
    item_id: int
    telegram_file_id: str
    order: int

    created_at: AwareDatetime
    updated_at: AwareDatetime

    model_config = ConfigDict(from_attributes=True)