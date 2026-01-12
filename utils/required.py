from functools import wraps
from aiogram.types import Message
from typing import Callable, Awaitable
import logging

from services.user_service import UserService

# !!!!!!!!!!!!! ЭТУ ЛОГИКУ ЗАМЕНИЛИ ЧЕРЕЗ MIDDLEWARE (registration_check)
# еще обдумать нужно будет:
def registration_required(func: Callable[..., Awaitable]):
    """Декоратор: проверяет регистрацию пользователя перед вызовом хендлера"""

    @wraps(func)
    async def wrapper(message: Message, *args, **kwargs):
        user_service: UserService = kwargs.get("user_service")
        user = await user_service.get_by_telegram_id(message.from_user.id)

        if not user or not user.phone:
            await message.answer(
                "⚠️ Для доступа к этому разделу необходимо пройти регистрацию.\n"
                "Введите /start, чтобы зарегистрироваться."
            )
            return

        return await func(message, *args, **kwargs)

    return wrapper
