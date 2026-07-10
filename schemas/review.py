from typing import Optional
from pydantic import BaseModel, Field, AwareDatetime, ConfigDict

from status.review_status import ReviewStatus

"""
    ReviewCreate          → клиент создаёт отзыв
    ReviewUpdate          → клиент обновляет отзыв до публикации
    ReviewOut             → базовый вывод отзыва наружу
    ReviewCreateInternal  → внутренняя схема создания отзыва с user_id
    ReviewAdminUpdate     → админская модерация отзыва
"""

class ReviewCreate(BaseModel):
    """Клиентская схема для создания отзыва по завершённой заявке."""

    rental_id: int
    item_id: Optional[int] = None
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None


class ReviewUpdate(BaseModel):
    """Схема для обновления текста и оценки отзыва клиентом до публикации."""

    rating: Optional[int] = Field(None, ge=1, le=5)
    comment: Optional[str] = None


class ReviewOut(BaseModel):
    """Схема для возврата отзыва наружу"""

    id: int
    rental_id: int
    item_id: Optional[int] = None
    user_id: int
    rating: int
    comment: Optional[str] = None
    status: ReviewStatus
    admin_note: Optional[str] = None

    created_at: AwareDatetime
    updated_at: AwareDatetime

    model_config = ConfigDict(from_attributes=True)


# ─────────────────────────────────────── Review Internal ──────────────────────────────────────────────────────────────
class ReviewCreateInternal(ReviewCreate):
    """Внутренняя схема создания отзыва с уже определённым клиентом."""

    user_id: int


# ─────────────────────────────────────── Review Admin ─────────────────────────────────────────────────────────────────
class ReviewAdminUpdate(BaseModel):
    """Схема для модерации отзыва администратором."""

    status: Optional[ReviewStatus] = None
    admin_note: Optional[str] = None