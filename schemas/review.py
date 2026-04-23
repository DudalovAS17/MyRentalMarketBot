from typing import Optional
from pydantic import BaseModel, Field, AwareDatetime, ConfigDict

class ReviewCreate(BaseModel):
    """Схема для создания отзыва"""

    rental_id: int
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None


class ReviewOut(BaseModel):
    """Схема для возврата отзыва наружу"""

    id: int
    rental_id: int
    reviewer_id: int
    reviewee_id: int
    rating: int
    comment: Optional[str] = None

    created_at: AwareDatetime
    updated_at: AwareDatetime

    model_config = ConfigDict(from_attributes=True)