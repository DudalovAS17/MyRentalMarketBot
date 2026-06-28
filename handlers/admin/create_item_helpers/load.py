from collections.abc import Awaitable, Callable
from typing import TypeVar
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup
from aiogram.exceptions import TelegramBadRequest

from handlers.admin.create_item_helpers.keyboard import build_create_item_categories_keyboard
from .texts import create_item_category_step_text
from services.category_service import CategoryService
from services.photo_service import PhotoService

from schemas.item import ItemOut
from utils.functions import send_or_edit
from utils.errors import ServiceError

T = TypeVar("T")

# ─────────────────────────────────────────────────show─────────────────────────────────────────────────────────────────
async def load_item(
        callback: CallbackQuery,
        loader: Callable[[int], Awaitable[T | None]],
        entity_id: int | None,
        invalid_id_text: str,
        load_error_text: str,
        not_found_text: str,
        markup_back: InlineKeyboardMarkup,
) -> list[T] | None:
    """Загрузить item или показать UX-ошибку"""
    if entity_id is None:
        await send_or_edit(callback, invalid_id_text)
        return None

    try:
        entity = await loader(entity_id)
    except ServiceError:
        await send_or_edit(callback, load_error_text)
        return None

    if entity is None:
        await send_or_edit(callback, not_found_text, markup=markup_back)
        return None

    return entity


async def load_item_category_context(category_service: CategoryService, item: ItemOut) -> tuple[str, str]:
    """Получить названия категории и подкатегории для карточки item"""
    try:
        category = await category_service.get_category_by_id(item.category_id) if item.category_id else None
        subcategory = await category_service.get_category_by_id(item.subcategory_id) if item.subcategory_id else None
    except ServiceError:
        return "-", "-"

    category_name = category.name if category else "-"
    subcategory_name = subcategory.name if subcategory else "-"
    return category_name, subcategory_name

# ─────────────────────────────────────────────────flow_create──────────────────────────────────────────────────────────
async def show_create_item_categories_step(callback: CallbackQuery, category_service: CategoryService) -> None:
    """Показать шаг выбора категории при создании объявления"""
    try:
        categories = await category_service.list_main_categories()
    except ServiceError:
        await send_or_edit(callback, "⚠️ Не удалось загрузить категории. Попробуйте позже.")
        return

    await send_or_edit(
        callback,
        create_item_category_step_text(),
        markup=build_create_item_categories_keyboard(categories)
    )


async def load_entity_or_notify(
        callback: CallbackQuery,
        loader: Callable[[int], Awaitable[T | None]],
        entity_id: int | None,
        invalid_id_text: str,
        load_error_text: str,
        not_found_text: str
) -> T | None:
    """Загрузить сущность через loader или показать UX-ошибку"""
    if entity_id is None:
        await send_or_edit(callback, invalid_id_text)
        return None

    try:
        entity = await loader(entity_id)
    except ServiceError:
        await send_or_edit(callback, load_error_text)
        return None

    if entity is None:
        await send_or_edit(callback, not_found_text)
        return None

    return entity


async def send_item_confirmation_preview(*, message: Message, text: str, photos: list[str], keyboard: InlineKeyboardMarkup) -> None:
    """Отправить preview объявления с фото или текстовым fallback"""
    if photos:
        try:
            await message.answer_photo(
                photo=photos[0],
                caption=text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            return
        except TelegramBadRequest:
            # если caption/фото не прошло — покажем текстом
            pass

    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


async def attach_item_photos_or_warn(
    callback: CallbackQuery,
    photo_service: PhotoService,
    item_id: int,
    photos: list[str]
) -> None:
    """Прикрепить фото к созданному объявлению или предупредить пользователя"""

    valid_photos = [photo for photo in photos if isinstance(photo, str) and photo.strip()]
    if not valid_photos:
        return

    try:
        await photo_service.create_photos(item_id, valid_photos)
    except ServiceError:
        if callback.message:
            await callback.message.answer(
                "⚠️ Объявление создано, но фото не удалось сохранить. Попробуйте добавить их позже.",
                parse_mode="HTML",
            )