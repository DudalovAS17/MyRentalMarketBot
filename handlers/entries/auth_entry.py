from aiogram.types import Message

from handlers.entries.entry_helper import build_registration_welcome_text, build_registration_contact_keyboard
from services.user_service import UserService
from schemas.user import UserCreate
from utils.functions import send_reply
from utils.errors import ServiceError

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
        await user_service.create(user_data)
    except ServiceError:
        await send_reply(message, "⚠️ Не удалось начать регистрацию. Попробуйте позже или используйте /start для входа в меню.")
        return

    # запрашиваем телефон пользователя
    await message.answer(
        build_registration_welcome_text(),
        reply_markup=build_registration_contact_keyboard(),
        arse_mode="HTML"
    )