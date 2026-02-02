import logging
from typing import Any, Awaitable, Callable, Dict, Union

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery

from services.user_service import UserService

from utils.functions import deny
from utils.user_status import BANNED

logger = logging.getLogger(__name__)


class RegistrationCheckMiddleware(BaseMiddleware):
    """
    Middleware, проверяющее регистрацию и блокировку пользователя перед вызовом хендлеров.

    🔹 Проверяет наличие пользователя в БД
    🔹 Проверяет наличие телефона (регистрация завершена)
    🔹 Проверяет блокировку
    🔹 Если всё ок — добавляет `user` в data
    """

    def __init__(self, user_service: UserService): # , skip_commands: tuple[str, ...] = ("/start", "/register")
        super().__init__()
        self.user_service = user_service
        #self.skip_commands = skip_commands  # команды, которые пропускаются без проверки

    async def __call__(
        self,
        handler: Callable[[Union[Message, CallbackQuery], Dict[str, Any]], Awaitable[Any]],
            # следующий обработчик в цепочке (следующий middleware или уже хендлер)
        event: Union[Message, CallbackQuery],
        data: Dict[str, Any], # DI-контейнер (в него можно докладывать переменные,
            # которые затем будут инжектиться в хендлер как параметры - user, user_service, и т.д.)
    ) -> Any:
        """Основная точка входа в middleware"""

        # 🧠 Определяем Telegram ID пользователя
        user_id = getattr(event.from_user, "id", None)
        if not user_id:
            logger.warning("[Middleware] event without user_id, blocked")
            return None

        # 1️⃣ Пропускаем команду /start без проверки
        if isinstance(event, Message) and event.text and event.text.startswith("/start"):
            return await handler(event, data)
        # Чтобы новые пользователи могли вызвать /start без «предварительной регистрации»

        # 2️⃣ Пропускаем любые сообщения, содержащие контакт (иначе регистрацию никогда не завершить.)
        if isinstance(event, Message) and event.contact:
            return await handler(event, data)

        user = await self.user_service.get_by_telegram_id(user_id)

        # deny() - цель: “остановить цепочку и объяснить пользователю почему”

        # 🧩 Проверяем наличие пользователя в базе
        if not user:
            logger.info(f"[Middleware] Пользователь {user_id} не найден → предложить регистрацию")
            await deny(event,
                        "⚠️ Для доступа к функциям необходимо пройти регистрацию.\n"
                        "Введите /start, чтобы зарегистрироваться."
                        ) # ❌ Ваш профиль не найден. Пожалуйста, зарегистрируйтесь через /start.
            return None # Прерываем выполнение цепочки — хендлер не вызывается


        # ──────────────────────────────────────────── NEW (Admin-User logic) ──────────────────────────────────────
        admin_ids = set(data.get("admin_ids") or []) # типо защитит от admin_ids = None/str
        #data.get("admin_ids", set())
        is_admin = user_id is not None and int(user_id) in admin_ids

        # если добавить поле is_admin в модель, то можно (не обязательно, но поднимает устойчивость):
        #is_admin = bool(getattr(user, "is_admin", False)) or (user_id is not None and int(user_id) in admin_ids)

        # 🚫 Проверка статуса аккаунта (блокируем всех, кроме админов)
        if getattr(user, "account_status", None) == BANNED and not is_admin:
            logger.warning(
                "[Middleware] BANNED пользователь %s попытался выполнить действие",
                user_id,
            )
            await deny(event, "Доступ ограничен. Обратитесь в поддержку.")
            return None
        # ──────────────────────────────────────────────────────────────────────────────────────────────────────────────


        # 🚫 Проверка блокировки
        if getattr(user, "is_blocked", False):
            logger.warning(f"[Middleware] Заблокированный пользователь {user_id} попытался выполнить действие")
            await deny(event,
                       "🚫 Ваша учётная запись заблокирована.\n"
                        "Если вы считаете, что это ошибка — обратитесь в поддержку."
                       )
            return None

        # 🚫 Проверка подтверждения телефона (без телефона — не даём пользоваться ботом)
        if not getattr(user, "phone", None):
            logger.info(f"[Middleware] Пользователь {user_id} не завершил регистрацию (нет телефона)")
            await deny(event,
                       "📱 Пожалуйста, подтвердите номер телефона, чтобы продолжить.\n"
                       "Введите /start и завершите регистрацию."
                       )
            return None
        # Если хотим, чтобы некоторые команды работали без телефона, нужно расширять skip_commands

        # ✅ Всё хорошо → добавляем пользователя в data
        """
        Middleware кладёт значения в data (обычный dict).
        Когда вызывается хендлер, aiogram смотрит на имена параметров функции и пытается найти в data ключи 
        с такими же именами.
        
        aiogram делает примерно так (упрощённо):
            видит параметр item_service → ищет data["item_service"]
            видит параметр user → ищет data["user"]
            видит параметр callback → это сам event
        Поэтому у тебя user подставляется автоматически.
        (DI — это Dependency Injection, внедрение зависимостей)
        
        ✅ Вывод: имя параметра должно совпадать с ключом в data
        
        Но помни! data — общий мешок, в который пишут разные middleware, конфликтов избегай
        """
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