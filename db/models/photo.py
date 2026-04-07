from __future__ import annotations

from typing import TYPE_CHECKING
from sqlalchemy import Integer
from sqlalchemy import ForeignKey, String, Index, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from db.models.item import Item


class Photo(Base, TimestampMixin):
    """Фотография, привязанная к объявлению (Item)"""

    __tablename__ = "photos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    item_id: Mapped[int] = mapped_column(
        ForeignKey("items.id", ondelete="CASCADE"),
        nullable=False
    )

    # идентификатор файла, который Telegram позволяет использовать повторно
    telegram_file_id: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Telegram file_id, который позволяет отправлять фото без повторной загрузки"
    )

    # порядок отображения фотографии внутри вещи (позволяет сортировать фото, например какое показывать первым)
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # ------- Отношения | связи --------

    # каждая фотография знает, к какой вещи относится
    item: Mapped["Item"] = relationship("Item", back_populates="item_photos")

    __table_args__ = (
        # быстрый поиск всех фото по item_id (создаёт в базе индекс на колонку item_id)
        Index("ix_photos_item_order", "item_id", "order"),

        # Чтобы не было отрицательных значений порядка
        CheckConstraint('"order" >= 0', name="ck_photos_order_non_neg")
    )