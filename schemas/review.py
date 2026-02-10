from typing import Optional

from pydantic import BaseModel, Field, AwareDatetime, ConfigDict

class ReviewCreate(BaseModel):
    """Схема для создания отзыва"""

    rental_id: int
    #reviewer_id: int ❌
    #reviewee_id: int ❌

    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None
# reviewer_id - из контекста авторизации или из Telegram-пользователя, но в сервисе
# reviewee_id - всегда определяется сделкой


# если будет нужно - вмешательство в отзыв
class ReviewUpdate(BaseModel):
    """Схема для обновления отзыва"""

    rating: Optional[int] = Field(None, ge=1, le=5)
    comment: Optional[str] = None


class ReviewOut(BaseModel):
    """Схема для возврата отзыва"""

    id: int
    rental_id: int
    reviewer_id: int
    reviewee_id: int
    rating: int
    comment: Optional[str] = None
    created_at: AwareDatetime
    updated_at: AwareDatetime

    model_config = ConfigDict(from_attributes=True)
