from aiogram import F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from .router import auth_router

from .helpers_auth.keyboards import build_change_phone_keyboard, build_open_profile_keyboard
from .helpers_auth.texts import build_invalid_contact_text, build_phone_changed_success_text, build_change_phone_prompt_text
from .helpers_auth.validation import is_own_contact
from services.user_service import UserService

from states.user import ProfileEditStates
from schemas.user import UserUpdate


@auth_router.callback_query(F.data == "profile_change_phone")
async def request_phone_number_change(callback: CallbackQuery, state: FSMContext) -> None:
    """Запрашивает новый номер телефона для смены номера в профиле"""
    await callback.answer()

    await state.set_state(ProfileEditStates.waiting_for_phone)

    # Показываем пользователю запрос
    await callback.message.answer(build_change_phone_prompt_text(), reply_markup=build_change_phone_keyboard(), parse_mode="HTML")


@auth_router.message(ProfileEditStates.waiting_for_phone, F.contact)
async def process_phone_number(message: Message, state: FSMContext, user_service: UserService, user) -> None:
    """Обработать новый контакт-телефон пользователя."""

    contact = message.contact
    phone_number = contact.phone_number
    tg_user = message.from_user

    # Проверка корректности контакта
    if not is_own_contact(contact, tg_user):
        await message.answer(build_invalid_contact_text(), reply_markup=build_change_phone_keyboard(), parse_mode="HTML")
        return # FSM остаётся в том же состоянии (ожидает контакт)

    # Обновляем телефон
    updated = await user_service.update(user.id,  UserUpdate(phone=phone_number))
    if not updated:
        await message.answer("❌ Ошибка при сохранении номера. Попробуйте позже.")
        return

    await state.clear()
    await message.answer(build_phone_changed_success_text(phone_number), parse_mode="HTML")

    await message.answer("🔙 Возвращаем вас в профиль...", reply_markup=build_open_profile_keyboard())
    return