from sqlalchemy import Column, Integer, String, Float, ForeignKey, Text, CheckConstraint, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.models.base import Base, TimestampMixin


class Review(Base, TimestampMixin):
    """Модель для хранения отзывов о (завершённых?) сделках аренды"""
    __tablename__ = 'reviews'

    id: Mapped[int] = mapped_column(primary_key=True)

    # Связь со сделкой
    rental_id: Mapped[int] = mapped_column(
        ForeignKey("rentals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Кто оставил отзыв
    reviewer_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Кому оставлен отзыв
    reviewee_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Оценка
    rating: Mapped[int] = mapped_column(nullable=False) # Оценка от 1 до 5

    # Текст отзыва
    comment: Mapped[str | None] = mapped_column(Text, nullable=True) # Текстовый комментарий

    # Отношения
    rental = relationship("Rental", back_populates="reviews")

    reviewer = relationship(
        "User",
        foreign_keys=[reviewer_id],
        lazy="joined",
    )

    reviewee = relationship(
        "User",
        foreign_keys=[reviewee_id],
        lazy="joined",
    )

    __table_args__ = (
        # Рейтинг строго 1–5
        CheckConstraint(
            "rating >= 1 AND rating <= 5",
            name="ck_reviews_rating_range",
        ),

        # Один отзыв на сделку от одного пользователя (Без этого: пользователь сможет 10 раз нажать «Оставить отзыв»)
        UniqueConstraint(
            "rental_id",
            "reviewer_id",
            name="uq_reviews_rental_reviewer",
        ),
    )