from aiogram import F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from .router import auth_router

from .helpers_auth.texts import (build_edit_profile_menu_text, build_edit_name_prompt_text, build_edit_email_prompt_text,
                                 build_invalid_contact_text, build_phone_changed_success_text, build_change_phone_prompt_text)
from .helpers_auth.keyboards import (build_edit_profile_menu_keyboard, build_back_to_profile_keyboard,
                                     build_change_phone_keyboard, build_open_profile_keyboard)
from .helpers_auth.validation import validate_profile_name, validate_profile_email, is_own_contact
from services.user_service import UserService

from keyboards.common import profile_settings_back_keyboard
from schemas.user import UserUpdate
from utils.functions import send_or_edit
from utils.callbacks import PROFILE_EDIT_NAME, PROFILE_EDIT_PHONE, PROFILE_EDIT_EMAIL, PROFILE_EDIT
from states.user import ProfileEditStates

# тут нет вызова для message
@auth_router.callback_query(F.data == PROFILE_EDIT)
async def show_edit_profile_settings(event: Message | CallbackQuery, user) -> None:
    """Показывает под-меню редактирования профиля: имя, email, и т.д."""
    if isinstance(event, CallbackQuery):
        await event.answer()

    await send_or_edit(event, build_edit_profile_menu_text(user), build_edit_profile_menu_keyboard())

# ───────────────────────────────────────────── FSM: edit name ─────────────────────────────────────────────────────────
@auth_router.callback_query(F.data == PROFILE_EDIT_NAME)
async def ask_new_name(callback: CallbackQuery, state: FSMContext) -> None:
    """Запросить новое имя пользователя"""
    await callback.answer()

    await state.set_state(ProfileEditStates.waiting_for_name)

    await send_or_edit( # callback.message.edit_text
        callback,
        build_edit_name_prompt_text(),
        markup=profile_settings_back_keyboard(),
    )

@auth_router.message(ProfileEditStates.waiting_for_name, F.text)
async def process_edit_name(message: Message, state: FSMContext, user_service: UserService, user) -> None:
    """Обрабатывает ввод нового имени пользователя (редактирование профиля)"""

    new_name = (message.text or "").strip()

    validation_error = validate_profile_name(new_name)
    if validation_error:
        await message.answer(validation_error)
        return

    full_name = f"{user.first_name or ''} {new_name}".strip()

    # Обновление
    updated = await user_service.update(
        user.id,
        UserUpdate(full_name=full_name)
    )

    if not updated:
        await message.answer("⚠️ Не удалось сохранить имя. Попробуйте позже.")
        return

    await state.clear()
    await message.answer(f"✅ Ваше имя успешно изменено на <b>{new_name}</b>.", parse_mode="HTML") # reply_markup=ReplyKeyboardRemove()

    # показываем обновлённый профиль
    await message.answer("🔙 Возвращаемся в профиль...", reply_markup=build_back_to_profile_keyboard())

# ───────────────────────────────────────────── FSM: edit email ────────────────────────────────────────────────────────
@auth_router.callback_query(F.data == PROFILE_EDIT_EMAIL)
async def ask_new_email(callback: CallbackQuery, state: FSMContext) -> None:
    """Запросить новый email пользователя"""
    await callback.answer()

    await state.set_state(ProfileEditStates.waiting_for_email)

    await send_or_edit( # callback.message.edit_text
        callback,
        build_edit_email_prompt_text(),
        markup=profile_settings_back_keyboard(),
    )

@auth_router.message(ProfileEditStates.waiting_for_email, F.text)
async def process_edit_email(message: Message, state: FSMContext, user_service: UserService, user) -> None:
    """Обрабатывает ввод нового email. Работает только если FSM находится в режиме редактирования email."""

    new_email = (message.text or "").strip()

    validation_error = validate_profile_email(new_email)
    if validation_error:
        await message.answer(validation_error)
        return

    # Обновление
    updated = await user_service.update(
        user.id,
        UserUpdate(email=new_email)
    )

    if not updated:
        await message.answer("⚠️ Не удалось сохранить email. Попробуйте позже.")
        return

    await state.clear()
    await message.answer(f"✅ Ваш email успешно обновлён на <b>{new_email}</b>.", parse_mode="HTML") # reply_markup=ReplyKeyboardRemove()

    # показываем обновлённый профиль
    await message.answer("🔙 Возвращаем вас в профиль...", reply_markup=build_back_to_profile_keyboard())

# ───────────────────────────────────────────── FSM: edit phone ────────────────────────────────────────────────────────
@auth_router.callback_query(F.data == PROFILE_EDIT_PHONE)
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

@auth_router.message(ProfileEditStates.waiting_for_phone)
async def process_invalid_phone_input(message: Message) -> None:
    """Обработать неверный ввод при ожидании контакта."""
    await message.answer(
        "📱 Пожалуйста, отправьте номер через кнопку <b>«Поделиться контактом»</b>.",
        reply_markup=build_change_phone_keyboard(),
        parse_mode="HTML",
    )