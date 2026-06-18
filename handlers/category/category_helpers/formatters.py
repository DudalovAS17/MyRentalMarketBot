from collections.abc import Sequence
from aiogram.types import InputMediaPhoto

from schemas.photo import PhotoOut
from schemas.rental import RentalOut

def busy_until_text(open_rental: RentalOut | None) -> str | None:
    """Вернуть дату окончания открытой заявки в формате dd.mm.YYYY"""
    if not open_rental or not getattr(open_rental, "end_date", None):
        return None
    return open_rental.end_date.strftime("%d.%m.%Y")

def get_photo_source(photo: PhotoOut) -> str | None:
    """Вернуть источник фото: telegram_file_id или внешний URL."""
    if photo is None:
        return None

    return photo.telegram_file_id or photo.url

def build_photo_media(photos: Sequence[PhotoOut]) -> list[InputMediaPhoto]:
    """Собрать media group для отправки фотографий товара"""
    media: list[InputMediaPhoto] = []

    for photo in photos:
        photo_source = get_photo_source(photo)

        if not photo_source:
            continue

        media.append(InputMediaPhoto(media=photo_source))

    return media

