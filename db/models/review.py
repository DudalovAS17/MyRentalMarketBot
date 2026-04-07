from __future__ import annotations

from typing import TYPE_CHECKING
from sqlalchemy import Index, Integer, ForeignKey, Text, CheckConstraint, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from db.models.user import User
    from db.models.rental import Rental


class Review(Base, TimestampMixin):
    """Модель для хранения отзывов о сделках аренды"""
    __tablename__ = 'reviews'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Связь со сделкой (Review у тебя привязан не просто к пользователю, а именно к факту сделки)
    rental_id: Mapped[int] = mapped_column(ForeignKey("rentals.id", ondelete="CASCADE"), nullable=False)

    # Кто оставил отзыв
    reviewer_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)

    # Кому оставлен отзыв
    reviewee_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"),  nullable=False)

    # Оценка (от 1 до 5)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)

    # Текст отзыва (Текстовый комментарий)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)


    # ------- Отношения | связи --------

    # отзыв знает, к какой аренде он относится
    rental: Mapped["Rental"] = relationship("Rental", back_populates="reviews")

    reviewer: Mapped["User"] = relationship("User", foreign_keys=[reviewer_id])
    reviewee: Mapped["User"] = relationship("User", foreign_keys=[reviewee_id])

    __table_args__ = (
        Index("ix_reviews_rental_id", "rental_id"),
        Index("ix_reviews_reviewer_id", "reviewer_id"),
        Index("ix_reviews_reviewee_id", "reviewee_id"),

        # Рейтинг строго 1–5
        CheckConstraint("rating >= 1 AND rating <= 5", name="ck_reviews_rating_range"),

        # Один отзыв на сделку от одного пользователя (Без этого: пользователь сможет 10 раз нажать «Оставить отзыв»)
        UniqueConstraint("rental_id", "reviewer_id", name="uq_reviews_rental_reviewer"),

        # Быстрые выборки:
        # рейтинг пользователя
        Index("ix_reviews_reviewee_rating", "reviewee_id", "rating"),
        # связка сделка+получатель
        Index("ix_reviews_rental_reviewee", "rental_id", "reviewee_id"),
    )