from aiogram import F
from aiogram.types import Message

from handlers.entries import show_main_menu, start_registration
from handlers.entry_helper import is_own_contact
from services.user_service import UserService, can_use_bot

from keyboards.common import build_registration_contact_keyboard
from schemas.user import UserUpdate

from .router import auth_router

# проверь
@auth_router.message(F.contact)
async def complete_registration_with_contact(message: Message, user_service: UserService) -> None:
    """Завершает регистрацию по присланному контакту."""
    contact = message.contact
    tg_user = message.from_user

    if not is_own_contact(contact, tg_user):
        await message.answer(
            "❌ Пожалуйста, отправьте именно свой контакт через кнопку ниже.",
            reply_markup=build_registration_contact_keyboard(),
        )
        return

    user = await user_service.get_by_telegram_id(tg_user.id)
    if not user:
        await start_registration(message, user_service)
        return

    await user_service.update(user.id, UserUpdate(phone=contact.phone_number))
    updated_user = await user_service.get_by_telegram_id(tg_user.id, strict=True)

    if not can_use_bot(updated_user.account_status):
        await message.answer(
            "⛔ Ваш аккаунт заблокирован. Если это ошибка, свяжитесь с поддержкой.",
            parse_mode="HTML",
        )
        return

    await message.answer("✅ Номер подтверждён. Регистрация завершена.")
    await show_main_menu(message, updated_user)