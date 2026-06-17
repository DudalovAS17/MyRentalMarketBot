from collections.abc import Sequence
from aiogram.types import InputMediaPhoto

from schemas.photo import PhotoOut
from schemas.rental import RentalOut

def busy_until_text(open_rental: RentalOut | None) -> str | None:
    """Вернуть дату окончания открытой заявки в формате dd.mm.YYYY"""
    if not open_rental or not getattr(open_rental, "end_date", None):
        return None
    return open_rental.end_date.strftime("%d.%m.%Y")

def build_photo_media(photos: Sequence[PhotoOut]) -> list[InputMediaPhoto]:
    """Собрать media group для отправки фотографий товара"""
    return [
        InputMediaPhoto(media=photo.telegram_file_id)
        for photo in photos
        if photo.telegram_file_id or photo.url
    ]