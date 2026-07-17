from typing import Any
from aiogram.types import CallbackQuery, InputMediaPhoto, InputRichMessage
from aiogram.exceptions import TelegramBadRequest

from handlers.category.category_helpers.formatters import get_photo_source
from schemas.photo import PhotoOut


async def send_or_edit_item_card(callback: CallbackQuery, photos: list[PhotoOut], text: str, markup) -> None:
    """Показать rich-карточку товара с фото внутри rich-сообщения."""

    photo_source = build_rich_photo_sources(photos)
    rich_message = build_rich_item_card_message(text, photo_source)

    message = callback.message
    if message is None:
        return

    try:
        # Rich Message API отправляется не через caption/parse_mode, а отдельным rich_message.
        # Если до этого на экране было фото-сообщение, редактировать его в rich-сообщение нельзя — заменяем.
        if message.photo:
            await replace_with_rich_message(message, rich_message, markup)
            return

        await message.edit_text(
            rich_message=rich_message,
            reply_markup=markup,
            parse_mode=None,
        )

    except TelegramBadRequest as error:
        if "message is not modified" in str(error).lower():
            return

        # Если Telegram отклонил rich-фото, повторяем эту же rich-карточку без медиа.
        # Ошибки RICH_MESSAGE_PHOTO_* возникают только из-за медиа-блока, не из-за таблиц/заголовков.
        if "RICH_MESSAGE_PHOTO" in str(error):
            rich_message = build_rich_item_card_message(text, [])

        # Fallback: если Telegram не смог отредактировать сообщение, заменяем его, чтобы не плодить дублей.
        try:
            await replace_with_rich_message(message, rich_message, markup)
        except TelegramBadRequest as fallback_error:
            if "RICH_MESSAGE_PHOTO" not in str(fallback_error):
                raise

            await replace_with_rich_message(message, build_rich_item_card_message(text, []), markup)


# ───────────────────────────────────────────── helpers for helper ─────────────────────────────────────────────────────
def build_rich_photo_sources(photos: list[PhotoOut]) -> list[str]:
    """Собрать источники фото, пригодные для InputMediaPhoto в rich-сообщении."""
    photo_sources: list[str] = []

    for photo in photos:
        photo_source = get_photo_source(photo)
        if photo_source:
            photo_sources.append(photo_source)

    return photo_sources


def build_rich_item_card_message(text: str, photo_sources: list[str]) -> InputRichMessage:
    """Собрать rich-сообщение и явно привязать медиа для HTML-ссылки tg://photo?id=... ."""
    kwargs: dict[str, Any] = {
        "html": build_rich_item_card_html(text, photo_sources),
        "skip_entity_detection": True,
    }

    if photo_sources:
        kwargs["media"] = [
            {
                "id": build_rich_photo_id(index),
                "media": InputMediaPhoto(media=photo_source)
            }
            for index, photo_source in enumerate(photo_sources)
        ]

    return InputRichMessage(**kwargs)


def build_rich_item_media_html(photo_sources: list[str]) -> str:
    """Сформировать rich-блок медиа: одно фото или slideshow для нескольких фото."""
    if not photo_sources:
        return ""

    if len(photo_sources) == 1:
        return f'<img src="tg://photo?id={build_rich_photo_id(0)}">\n'

    image_tags = "\n".join(
        f'  <img src="tg://photo?id={build_rich_photo_id(index)}">'
        for index, _ in enumerate(photo_sources)
    )
    return f"<tg-slideshow>\n{image_tags}\n</tg-slideshow>\n"


RICH_ITEM_PHOTO_ID_PREFIX = "item_photo"
def build_rich_photo_id(index: int) -> str:
    """Вернуть стабильный id rich-медиа для фото товара."""
    return f"{RICH_ITEM_PHOTO_ID_PREFIX}_{index}"

def build_rich_item_card_html(text: str, photo_sources: list[str]) -> str:
    """Добавить rich-медиа товара перед текстом карточки."""
    return f"{build_rich_item_media_html(photo_sources)}{text}"

async def replace_with_rich_message(message, rich_message: InputRichMessage, markup) -> None:
    """Заменить текущее сообщение rich-карточкой без накопления дублей."""
    try:
        await message.delete()
    except TelegramBadRequest:
        pass

    await message.answer_rich(rich_message=rich_message, reply_markup=markup)