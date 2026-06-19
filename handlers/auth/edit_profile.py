from aiogram import F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from .router import auth_router

from .helpers_auth.texts import build_edit_profile_menu_text, build_edit_name_prompt_text, build_edit_email_prompt_text
from .helpers_auth.keyboards import build_edit_profile_menu_keyboard, build_back_to_profile_keyboard
from .helpers_auth.validation import validate_profile_name, validate_profile_email
from services.user_service import UserService

from schemas.user import UserUpdate
from utils.functions import send_or_edit
from states.user import ProfileEditStates
from keyboards.common import profile_settings_back_keyboard


# тут нет вызова для message
@auth_router.callback_query(F.data == "settings_edit_profile")
async def show_edit_profile_settings(event: Message | CallbackQuery, user) -> None:
    """Показывает под-меню редактирования профиля: имя, email, и т.д."""
    if isinstance(event, CallbackQuery):
        await event.answer()

    await send_or_edit(event, build_edit_profile_menu_text(user), build_edit_profile_menu_keyboard())

# ────────────────────────────────────────────────── edit name ─────────────────────────────────────────────────────────
@auth_router.callback_query(F.data == "edit_profile_field:name")
async def ask_new_name(callback: CallbackQuery, state: FSMContext) -> None:
    """Запросить новое имя пользователя"""
    await callback.answer()

    await state.set_state(ProfileEditStates.waiting_for_name)

    await callback.message.edit_text(
        build_edit_name_prompt_text(),
        reply_markup=profile_settings_back_keyboard(),
        parse_mode="HTML"
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
        UserUpdate(last_name=new_name, full_name=full_name)
    )

    if not updated:
        await message.answer("⚠️ Не удалось сохранить имя. Попробуйте позже.")
        return

    await state.clear()
    await message.answer(f"✅ Ваше имя успешно изменено на <b>{new_name}</b>.", parse_mode="HTML")

    # показываем обновлённый профиль
    await message.answer("🔙 Возвращаемся в профиль...", reply_markup=build_back_to_profile_keyboard())

# ────────────────────────────────────────────────── edit email ────────────────────────────────────────────────────────
@auth_router.callback_query(F.data == "edit_profile_field:email")
async def ask_new_email(callback: CallbackQuery, state: FSMContext) -> None:
    """Запросить новый email пользователя"""
    await callback.answer()

    await state.set_state(ProfileEditStates.waiting_for_email)

    await callback.message.edit_text(
        build_edit_email_prompt_text(),
        reply_markup=profile_settings_back_keyboard(),
        parse_mode="HTML"
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
    await message.answer(f"✅ Ваш email успешно обновлён на <b>{new_email}</b>.", parse_mode="HTML")

    # показываем обновлённый профиль
    await message.answer("🔙 Возвращаем вас в профиль...", reply_markup=build_back_to_profile_keyboard())