from aiogram import F
from aiogram.types import Message

from handlers.entries import show_main_menu #, start_registration
from handlers.entry_helper import is_own_contact
from services.user_service import UserService, can_use_bot

from keyboards.common import build_registration_contact_keyboard
from schemas.user import UserUpdate # UserCreate,
from utils.errors import ServiceError

from .router import auth_router

# проверь
@auth_router.message(F.contact)
async def complete_registration_with_contact(message: Message, user_service: UserService) -> None:
    """Завершает регистрацию по присланному контакту."""
    contact = message.contact
    tg_user = message.from_user

    if contact is None or tg_user is None:
        await message.answer(
            "❌ Не удалось получить контакт. Пожалуйста, отправьте номер через кнопку ниже.",
            reply_markup=build_registration_contact_keyboard(),
        )
        return

    if not is_own_contact(contact, tg_user):
        await message.answer(
            "❌ Пожалуйста, отправьте именно свой контакт через кнопку ниже.",
            reply_markup=build_registration_contact_keyboard(),
        )
        return

    try:
        user = await user_service.get_by_telegram_id(tg_user.id)
        if user is None:
            await message.answer(
                "⚠️ Сначала нажмите /start, чтобы создать профиль, а затем отправьте номер через кнопку."
            )
            return

        updated_user = await user_service.update(
            user.id,
            UserUpdate(
                username=tg_user.username,
                first_name=tg_user.first_name,
                last_name=tg_user.last_name,
                full_name=f"{tg_user.first_name or ''} {tg_user.last_name or ''}".strip(),
                phone=contact.phone_number,
                language_code=tg_user.language_code,
            ),
            strict=True,
        )
        if updated_user is None:
            raise ServiceError("Не удалось обновить телефон пользователя")
    except ServiceError:
        await message.answer("⚠️ Не удалось завершить регистрацию. Попробуйте позже.")
        return

    if not can_use_bot(updated_user.account_status):
        await message.answer(
            "⛔ Ваш аккаунт заблокирован. Если это ошибка, свяжитесь с поддержкой.",
            parse_mode="HTML",
        )
        return

    await message.answer("✅ Номер подтверждён. Регистрация завершена.")
    await show_main_menu(message, updated_user)