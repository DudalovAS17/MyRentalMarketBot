#from typing import Optional
from sqlalchemy import Integer
from sqlalchemy import ForeignKey, String, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.models.base import Base, TimestampMixin, ReprMixin, DictMixin


class Photo(Base, TimestampMixin, ReprMixin, DictMixin):
    """Фотография, привязанная к объявлению (Item)"""

    __tablename__ = "photos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    item_id: Mapped[int] = mapped_column(ForeignKey("items.id", ondelete="CASCADE"),
                                         nullable=False, index=True)
    # index=True → быстрый поиск всех фото по item_id (создаёт в базе индекс на колонку item_id)

    telegram_file_id: Mapped[str] = mapped_column(
        String(500),
        nullable=False, # Чтобы в коде не возникало None, которое ломает сортировку.
        comment="Telegram file_id, который позволяет отправлять фото без повторной загрузки"
    ) # здесь мы храним как file_id из Telegram, так и URL

    order: Mapped[int] = mapped_column(Integer, nullable=False, default=0,
                                       comment="позволяет сортировать фото (например, какое показывать первым)")

    # связь с Item
    item = relationship("Item", back_populates="item_photos")

    # Дополнительные индексы (опционально, но полезно)
    __table_args__ = (
        Index("ix_photos_item_order", "item_id", "order"),
        # SELECT * FROM photos WHERE item_id = 123 ORDER BY order;
    )
