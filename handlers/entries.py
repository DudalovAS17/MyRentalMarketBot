from aiogram.types import CallbackQuery, Message

from handlers.entry_helper import build_main_menu_text, build_registration_welcome_text
from services.category_service import CategoryService
from services.rental_service import RentalService
from services.user_service import UserService

from keyboards.common import (get_main_menu_keyboard, build_empty_my_rentals_keyboard, build_my_rentals_keyboard,
                              build_categories_screen_keyboard, build_registration_contact_keyboard)
from schemas.user import UserCreate
from utils.functions import send_reply, send_or_edit
from utils.errors import ServiceError


# ───────────────────────────────────────────────── Base ───────────────────────────────────────────────────────────────
async def show_main_menu(event: Message | CallbackQuery, user) -> None:
    """Показывает главное меню"""

    await send_reply(
        event,
        build_main_menu_text(user),
        markup=get_main_menu_keyboard()
    )


# ──────────────────────────────────────────────── Category ────────────────────────────────────────────────────────────
async def show_categories(event: Message | CallbackQuery, category_service: CategoryService) -> None:
    """Показывает список категорий для выбора"""

    if isinstance(event, CallbackQuery):
        await event.answer()

    try:
        categories = await category_service.list_main_categories()
    except ServiceError:
        await send_reply(event, "⚠️ Не удалось загрузить категории. Попробуйте позже.")
        return

    await send_reply(
        event,
        "🔍 <b>Арендовать</b>\n\nВыберите категорию:",
        markup=build_categories_screen_keyboard(categories)
    )


# ─────────────────────────────────────────────────── Rental ───────────────────────────────────────────────────────────
async def show_my_rentals(event: Message | CallbackQuery, rental_service: RentalService, user) -> None:
    """Показывает список заявок пользователя"""

    if isinstance(event, CallbackQuery):
        await event.answer()

    try:
        rentals = await rental_service.list_rentals_by_user(user.id)
    except ServiceError:
        await send_or_edit(event, "⚠️ Не удалось загрузить список заявок. Попробуйте позже.")
        return

    if not rentals:
        await send_or_edit(
            event,
            "📭 У вас пока нет активных или завершённых заявок.",
            markup = build_empty_my_rentals_keyboard()
        )
        return

    await send_or_edit(
        event,
        "<b>📋 Ваши заявки</b>\n\n Выберите заявку, чтобы открыть детали:",
        markup=build_my_rentals_keyboard(rentals, current_user_id=user.id)
    )


# ──────────────────────────────────────────────────── Auth ────────────────────────────────────────────────────────────
async def start_registration(message: Message, user_service: UserService) -> None:
    """Entry-point сценария первичной регистрации"""

    tg_user = message.from_user
    tg_id = tg_user.id

    user_data = UserCreate(
        telegram_id=tg_id,
        username=tg_user.username,
        first_name=tg_user.first_name,
        last_name=tg_user.last_name,
        full_name=f"{tg_user.first_name or ''} {tg_user.last_name or ''}".strip(),
        phone=None,
        email=None
    )

    try:
        await user_service.create(user_data) # .register_or_update_user(user_data)
    except ServiceError:
        await send_reply(message, "⚠️ Не удалось начать регистрацию. Попробуйте позже или используйте /start для входа в меню.")
        return

    # запрашиваем телефон пользователя
    await request_phone_confirmation(message)

async def request_phone_confirmation(message: Message) -> None:
    """Попросить пользователя подтвердить телефон через Telegram contact."""

    await message.answer(
        build_registration_welcome_text(),
        reply_markup=build_registration_contact_keyboard(),
        parse_mode="HTML"
    )