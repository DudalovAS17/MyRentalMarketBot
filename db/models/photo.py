from __future__ import annotations

from typing import Optional, TYPE_CHECKING
from sqlalchemy import Integer, ForeignKey, Boolean, String, Index, CheckConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from db.models.item import Item


class Photo(Base, TimestampMixin):
    """Фотография товара каталога"""

    __tablename__ = "photos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    item_id: Mapped[int] = mapped_column(
        ForeignKey("items.id", ondelete="CASCADE"),
        nullable=False
    )

    # идентификатор файла, который Telegram позволяет использовать повторно
    telegram_file_id: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Telegram file_id, который позволяет отправлять фото без повторной загрузки"
    )

    # ссылка на фото товара с сайта
    url: Mapped[Optional[str]] = mapped_column(
        String(1000),
        nullable=True,
        comment="URL фотографии, если изображение взято с сайта или внешнего источника",
    )

    # порядок отображения фотографии внутри карточки товара (позволяет сортировать фото, например какое показывать первым)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # у товара может быть несколько фото, но одно из них главное
    is_main: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


    # ------- Отношения | связи --------

    # каждая фотография знает, к какому товару относится
    item: Mapped["Item"] = relationship("Item", back_populates="photos")

    __table_args__ = (
        # быстрый поиск всех фото по item_id (создаёт в базе индекс на колонку item_id)
        Index("ix_photos_item_order", "item_id", "sort_order"),

        Index("ix_photos_item_main", "item_id", "is_main"),

        # only one main photo per item at DB or service level
        Index(
            "uq_photos_one_main_per_item",
            "item_id",
            unique=True,
            postgresql_where=text("is_main IS TRUE"),
        ),

        # Чтобы не было отрицательных значений порядка
        CheckConstraint("sort_order >= 0", name="ck_photos_order_non_neg"),

        # у фото должен быть хотя бы telegram_file_id или url
        CheckConstraint("(telegram_file_id IS NOT NULL) OR (url IS NOT NULL)", name="ck_photos_has_source"),
    )