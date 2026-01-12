import logging
from typing import Any, Awaitable, Callable, Dict, Union

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery

from services.user_service import UserService

logger = logging.getLogger(__name__)


class RegistrationCheckMiddleware(BaseMiddleware):
    """
    Middleware, проверяющее регистрацию и блокировку пользователя перед вызовом хендлеров.

    🔹 Проверяет наличие пользователя в БД
    🔹 Проверяет наличие телефона (регистрация завершена)
    🔹 Проверяет блокировку
    🔹 Если всё ок — добавляет `user` в data
    """

    def __init__(self, user_service: UserService, skip_commands: tuple[str, ...] = ("/start", "/register")):
        super().__init__()
        self.user_service = user_service
        self.skip_commands = skip_commands  # команды, которые пропускаются без проверки

    async def __call__(
        self,
        handler: Callable[[Union[Message, CallbackQuery], Dict[str, Any]], Awaitable[Any]],
        event: Union[Message, CallbackQuery],
        data: Dict[str, Any], # DI-контейнер (в него можно докладывать переменные, которые затем будут инжектиться в хендлер как параметры)
    ) -> Any:
        """Основная точка входа в middleware"""

        # 🧠 Определяем Telegram ID пользователя
        user_id = getattr(event.from_user, "id", None)
        if not user_id:
            return await handler(event, data)

        # 1️⃣ Пропускаем команды /start и /register без проверки
        if isinstance(event, Message) and event.text in self.skip_commands:
            return await handler(event, data)
        # Чтобы новые пользователи могли вызвать /start или /register без «предварительной регистрации»,
        # эти команды не блокируем

        # 2️⃣ Пропускаем любые сообщения, содержащие контакт
        if isinstance(event, Message) and event.contact:
            return await handler(event, data)

        # 🧩 Проверяем наличие пользователя в базе
        user = await self.user_service.get_by_telegram_id(user_id)

        if not user:
            logger.info(f"[Middleware] Пользователь {user_id} не найден → предложить регистрацию")
            await event.answer(
                "⚠️ Для доступа к функциям необходимо пройти регистрацию.\n"
                "Введите /start, чтобы зарегистрироваться."
            ) # ❌ Ваш профиль не найден. Пожалуйста, зарегистрируйтесь через /start.
            return  # Прерываем выполнение цепочки — хендлер не вызывается

        # 🚫 Проверка блокировки
        if getattr(user, "is_blocked", False):
            logger.warning(f"[Middleware] Заблокированный пользователь {user_id} попытался выполнить действие")
            await event.answer(
                "🚫 Ваша учётная запись заблокирована.\n"
                "Если вы считаете, что это ошибка — обратитесь в поддержку."
            )
            return


        # 🚫 Проверка подтверждения телефона (нужно ли тут?)
        if not getattr(user, "phone", None):
            logger.info(f"[Middleware] Пользователь {user_id} не завершил регистрацию (нет телефона)")
            await event.answer(
                "📱 Пожалуйста, подтвердите номер телефона, чтобы продолжить.\n"
                "Введите /start и завершите регистрацию."
            )
            return

        # ✅ Всё хорошо → добавляем пользователя в data
        data["user"] = user

        # ⚙️ Передаём управление хендлеру
        return await handler(event, data)


"""
1) Перехватывает каждый update до вызова твоего хендлера
Middleware работает как фильтр: всё сообщение сначала проходит через него.

2) Определяет Telegram ID пользователя
Если ID нет → пропускает update дальше.

3) Пропускает команды /start и /register без проверок
Это нужно, чтобы незарегистрированный пользователь мог запустить регистрацию

4) Проверяет, существует ли пользователь в БД
5) Проверяет: заблокирован ли пользователь
6) Проверяет: указан ли телефон (в хендлеры бот пускает только пользователей с завершённой регистрацией)

7) Если всё хорошо — кладёт user в data
8) Передаёт управление хендлеру

👉 Middleware гарантирует, что в хендлер попадут только полностью зарегистрированные и 
не заблокированные пользователи, 
а новый пользователь может пройти только /start → регистрацию.
"""