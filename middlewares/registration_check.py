import logging
from typing import Any, Awaitable, Callable, Union, FrozenSet

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery

from services.user_service import UserService
from status.user_status import AccountStatus
from utils.functions import deny

logger = logging.getLogger(__name__)

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

class RegistrationCheckMiddleware(BaseMiddleware):
    """
    Middleware, проверяющее регистрацию и блокировку пользователя перед вызовом хендлеров.

    1) Пропускает /start и сообщения с контактом (иначе регистрацию не завершить).
    2) Проверяет, что пользователь существует в БД.
    3) Проверяет ограничения (бан/блок/телефон) — админов пропускает.
    4) Если всё ок — кладёт `user` в data для DI в хендлеры.
    """

    def __init__(self, user_service: UserService, admin_ids: FrozenSet[int]): # , skip_commands: tuple[str, ...] = ("/start", "/register")
        super().__init__()
        self.user_service = user_service
        self._admin_ids = admin_ids
        #self.skip_commands = skip_commands # команды, которые пропускаются без проверки

    def _is_admin(self, tg_user_id: int) -> bool:
        return tg_user_id in self._admin_ids

    async def __call__(
        self,
        handler: Callable[[Union[Message, CallbackQuery], dict[str, Any]], Awaitable[Any]],
            # следующий обработчик в цепочке (следующий middleware или уже хендлер)
        event: Union[Message, CallbackQuery],
        data: dict[str, Any], # DI-контейнер (в него можно докладывать переменные,
            # которые затем -> в хендлер как параметры - user, user_service, и т.д.)
    ) -> Any:
        """Основная точка входа в middleware"""

        # Определяем Telegram ID пользователя
        tg_user_id = _tg_user_id(event)
        if not tg_user_id:
            logger.warning("[RegistrationCheck] event без tg_user_id, блокируем проход")
            return None # Прерываем выполнение цепочки — хендлер не вызывается

        # Пропускаем команду /start без проверки
        # Чтобы новые пользователи могли вызвать /start без «предварительной регистрации»
        if _is_start(event):
            return await handler(event, data)

        # Пропускаем любые сообщения, содержащие контакт (иначе регистрацию никогда не завершить.)
        if _is_contact_message(event):
            return await handler(event, data)

        user = await self.user_service.get_by_telegram_id(tg_user_id)

        # 🧩 Проверяем наличие пользователя в базе
        if not user:
            logger.info(f"[RegistrationCheck] Пользователь {tg_user_id} не найден → предложить регистрацию")
            await deny(event, MSG_NEED_REGISTER)
            return None # Прерываем выполнение цепочки — хендлер не вызывается

        # ──────────────────────────────────────────── NEW (Admin-User logic) ──────────────────────────────────────
        is_admin = self._is_admin(tg_user_id)

        # 🚫 Проверка статуса аккаунта (блокируем всех, кроме админов)
        if getattr(user, "account_status", None)  == AccountStatus.BANNED and not is_admin:
            logger.warning("[RegistrationCheck] BANNED пользователь %s попытался выполнить действие",tg_user_id)
            await deny(event, MSG_BANNED)
            return None
        # ──────────────────────────────────────────────────────────────────────────────────────────────────────────────

        # 🚫 Проверка подтверждения телефона (без телефона — не даём пользоваться ботом)
        if not getattr(user, "phone", None):
            logger.info(f"[RegistrationCheck] Пользователь {tg_user_id} не завершил регистрацию (нет телефона)")
            await deny(event,MSG_NEED_PHONE)
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



# deny() - цель: “остановить цепочку и объяснить пользователю почему”
MSG_NEED_REGISTER = (
    "⚠️ Для доступа к функциям необходимо пройти регистрацию.\n"
    "Введите /start, чтобы зарегистрироваться."
) # ❌ Ваш профиль не найден. Пожалуйста, зарегистрируйтесь через /start.
MSG_BANNED = "Доступ ограничен. Обратитесь в поддержку."
MSG_BLOCKED = (
    "🚫 Ваша учётная запись заблокирована.\n"
    "Если вы считаете, что это ошибка — обратитесь в поддержку."
)
MSG_NEED_PHONE = (
    "📱 Пожалуйста, подтвердите номер телефона, чтобы продолжить.\n"
    "Введите /start и завершите регистрацию."
)

def _tg_user_id(event: Message | CallbackQuery) -> int | None:
    return getattr(getattr(event, "from_user", None), "id", None)

def _is_start(event: Message | CallbackQuery) -> bool:
    return isinstance(event, Message) and bool(event.text) and event.text.startswith("/start")

def _is_contact_message(event: Message | CallbackQuery) -> bool:
    return isinstance(event, Message) and bool(event.contact)
