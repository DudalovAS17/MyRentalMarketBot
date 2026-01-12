from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

class ReviewCreate(BaseModel):
    """Схема для создания отзыва"""

    rental_id: int
    reviewer_id: int
    reviewee_id: int

    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None

# если будет нужно
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
    comment: Optional[str]

    created_at: datetime

    class Config:
        from_attributes = True
