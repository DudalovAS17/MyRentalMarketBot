from sqlalchemy import Integer
from sqlalchemy import ForeignKey, String, Index, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.models.base import Base, TimestampMixin


class Photo(Base, TimestampMixin):
    """Фотография, привязанная к объявлению (Item)"""

    __tablename__ = "photos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    item_id: Mapped[int] = mapped_column(ForeignKey(
        "items.id", ondelete="CASCADE"),
        nullable=False
    )

    telegram_file_id: Mapped[str] = mapped_column(
        String(500),
        nullable=False, # Чтобы в коде не возникало None, которое ломает сортировку.
        comment="Telegram file_id, который позволяет отправлять фото без повторной загрузки"
    ) # здесь мы храним как file_id из Telegram, так и URL

    order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="позволяет сортировать фото (например, какое показывать первым)"
    )

    # Отношения
    item = relationship("Item", back_populates="item_photos")

    __table_args__ = (
        # быстрый поиск всех фото по item_id (создаёт в базе индекс на колонку item_id)
        Index("ix_photos_item_order", "item_id", "order"),

        CheckConstraint('"order" >= 0', name="ck_photos_order_nonneg")
    )