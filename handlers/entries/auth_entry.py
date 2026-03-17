import logging

from aiogram.types import (
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)
from aiogram.fsm.context import FSMContext
from sqlalchemy.exc import IntegrityError

from schemas.user import UserCreate
from services.user_service import UserService


from schemas.user import UserOut
from handlers.base import show_main_menu

logger = logging.getLogger(__name__)


def build_registration_contact_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Отправить номер телефона", request_contact=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

def build_registration_welcome_text() -> str:
    return (
        "👋 Приветствуем в <b>Аренда.рф</b>!\n\n"
        "Здесь вы можете сдавать и арендовать вещи по всей России.\n\n"
        "Для безопасности, пожалуйста, подтвердите номер телефона:"
        # тут надо норм текст при для 1-й регистрации
    )

async def start_registration(
    message: Message,
    user_service: UserService,
):
    """ Entry-point сценария первичной регистрации.

    Только сценарий НОВОГО пользователя:
    - создаём запись
    - просим контакт (телефон)
    Никаких проверок блокировки/«уже зарегистрирован» — это задача /start.
    """
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
        # Регистрируем пользователя или получаем существующего
        await user_service.create(user_data)
        logger.info(f"Создан новый пользователь с Telegram ID %s", tg_id)
    except IntegrityError:
        # такой пользователь уже есть (дубликат telegram_id)
        logger.warning("Попытка повторной регистрации пользователя %s", tg_id)
        await message.answer("⚠️ Аккаунт уже существует. Используйте /start для входа в меню.")
        return

    # запрашиваем телефон пользователя
    keyboard = build_registration_contact_keyboard()
    await message.answer(build_registration_welcome_text(), reply_markup=keyboard, parse_mode="HTML")

    # FSM перейдёт в состояние PHONE_NUMBER позже (в обработчике контакта)