from __future__ import annotations

from typing import Optional, TYPE_CHECKING
from sqlalchemy import Index, Integer, ForeignKey, Text, CheckConstraint, UniqueConstraint, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from status.review_status import ReviewStatus
from db.models.base import Base, TimestampMixin, enum_values

if TYPE_CHECKING:
    from db.models.user import User
    from db.models.item import Item
    from db.models.rental import Rental


class Review(Base, TimestampMixin):
    """Отзыв клиента о товаре, заявке или сервисе компании."""
    __tablename__ = 'reviews'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # # Связь с заявкой (Review у тебя привязан не просто к пользователю, а именно к факту заявки)
    rental_id: Mapped[int] = mapped_column(ForeignKey("rentals.id", ondelete="CASCADE"), nullable=False)

    # отзыв клиента именно о товаре
    item_id: Mapped[Optional[int]] = mapped_column(ForeignKey("items.id", ondelete="SET NULL"), nullable=True)

    # Кто оставил отзыв
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)

    # Оценка (от 1 до 5)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)

    # Текст отзыва (Текстовый комментарий)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Отзывы лучше модерировать перед публикацией
    status: Mapped[ReviewStatus] = mapped_column( # NEW
        SAEnum(ReviewStatus, name="review_status", values_callable=enum_values),
        nullable=False,
        default=ReviewStatus.PENDING,
    )

    # админ может оставить внутреннюю заметку
    admin_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


    # ------- Отношения | связи --------

    # отзыв знает, к какой аренде он относится
    rental: Mapped["Rental"] = relationship("Rental", back_populates="reviews")

    user: Mapped["User"] = relationship("User", back_populates="reviews")
    item: Mapped[Optional["Item"]] = relationship("Item", back_populates="reviews")

    __table_args__ = (
        Index("ix_reviews_rental_id", "rental_id"),
        Index("ix_reviews_user_id", "user_id"),
        Index("ix_reviews_item_id", "item_id"),
        Index("ix_reviews_status", "status"),

        # рейтинг пользователя
        Index("ix_reviews_item_rating", "item_id", "rating"),
        # один отзыв клиента в рамках одной заявки
        Index("ix_reviews_rental_user", "rental_id", "user_id"),

        Index("ix_reviews_item_status", "item_id", "status"),


        # Рейтинг строго 1–5
        CheckConstraint("rating >= 1 AND rating <= 5", name="ck_reviews_rating_range"),

        # Один отзыв на заявку от одного пользователя (Без этого: пользователь сможет 10 раз нажать «Оставить отзыв»)
        UniqueConstraint("rental_id", "user_id", name="uq_reviews_rental_user"),
    )