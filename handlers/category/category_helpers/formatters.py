from aiogram.types import InputMediaPhoto

def busy_until_text(open_rental) -> str | None:
    """Вернуть дату окончания открытой аренды в формате dd.mm.YYYY"""
    if not open_rental or not getattr(open_rental, "end_date", None):
        return None
    return open_rental.end_date.strftime("%d.%m.%Y")

def build_photo_media(photos) -> list[InputMediaPhoto]:
    """Собрать media group для отправки фотографий объявления"""
    return [InputMediaPhoto(media=photo.telegram_file_id) for photo in photos]