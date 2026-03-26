from aiogram.types import InputMediaPhoto

def busy_until_text(open_rental) -> str | None: # open_rental: Any
    if not open_rental or not getattr(open_rental, "end_date", None):
        return None
    return open_rental.end_date.strftime("%d.%m.%Y")

def build_photo_media(photos) -> list[InputMediaPhoto]: # photos: Sequence[Any]
    return [InputMediaPhoto(media=photo.telegram_file_id) for photo in photos]