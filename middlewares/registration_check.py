import logging
from typing import Any, Awaitable, Callable, FrozenSet
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery

from services.user_service import UserService
from status.user_status import AccountStatus
from utils.functions import deny
from texts.text_middleware import MSG_NEED_REGISTER, MSG_BANNED, MSG_NEED_PHONE # , MSG_BLOCKED

logger = logging.getLogger(__name__)

class RegistrationCheckMiddleware(BaseMiddleware):
    """Проверяет доступ пользователя в рабочую часть бота.

    Middleware отвечает только за входной guard:
    - пропускает `/start`, чтобы пользователь мог начать регистрацию;
    - пропускает контакт от нового пользователя, чтобы он мог завершить регистрацию;
    - загружает пользователя через `UserService` и кладёт DTO `user` в `data`;
    - блокирует забаненных пользователей, кроме администраторов из whitelist;
    - блокирует пользователей без телефона, кроме события с контактом.
    """
    """
    Middleware, проверяющее регистрацию и блокировку пользователя перед вызовом хендлеров

    1) Пропускает /start и сообщения с контактом (иначе регистрацию не завершить)
    2) Проверяет, что пользователь существует в БД
    3) Проверяет ограничения (бан/блок/телефон) — админов пропускает
    4) Если всё ок — кладёт `user` в data для DI в хендлеры
    """

    def __init__(self, user_service: UserService, admin_ids: FrozenSet[int]) -> None:
        super().__init__()
        self.user_service = user_service
        self._admin_ids = admin_ids

    def _is_admin(self, tg_user_id: int) -> bool:
        return tg_user_id in self._admin_ids

    async def __call__(
        self,
        handler: Callable[[Message | CallbackQuery, dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: dict[str, Any],
    ) -> Any:
        """Основная точка входа в middleware"""

        # Определяем Telegram ID пользователя
        tg_user_id = _tg_user_id(event)
        if tg_user_id is None:
            logger.warning("[RegistrationCheck] event без tg_user_id, блокируем проход")
            return None # Прерываем выполнение цепочки — хендлер не вызывается

        # Пропускаем команду /start без проверки (чтобы новые пользователи могли вызвать /start)
        if _is_start_command(event):
            return await handler(event, data)

        # Проверяем наличие пользователя в базе
        user = await self.user_service.get_by_telegram_id(tg_user_id)
        if user is None:
            # Пропускаем любые сообщения, содержащие контакт (иначе регистрацию никогда не завершить)
            if _is_contact_message(event):
                return await handler(event, data)
        if not user:
            logger.info(f"[RegistrationCheck] Пользователь {tg_user_id} не найден → предложить регистрацию")
            await deny(event, MSG_NEED_REGISTER)
            return None # Прерываем выполнение цепочки — хендлер не вызывается

        # ✅ Всё хорошо → добавляем пользователя в data
        data["user"] = user

        # 🚫 Проверка статуса аккаунта (блокируем всех, кроме админов)
        is_admin = self._is_admin(tg_user_id)
        if user.account_status == AccountStatus.BANNED and not is_admin:
            logger.warning("[RegistrationCheck] BANNED пользователь %s попытался выполнить действие",tg_user_id)
            await deny(event, MSG_BANNED)
            return None

        # 🚫 Проверка подтверждения телефона (без телефона — не даём пользоваться ботом)
        if not user.phone and not _is_contact_message(event):
            logger.info(f"[RegistrationCheck] Пользователь {tg_user_id} не завершил регистрацию (нет телефона)")
            await deny(event, MSG_NEED_PHONE)
            return None

        # ⚙️ Передаём управление хендлеру
        return await handler(event, data)

# ───────────────────────────────────────── helpers ────────────────────────────────────────────────────────────────────
def _tg_user_id(event: Message | CallbackQuery) -> int | None:
    return getattr(getattr(event, "from_user", None), "id", None)

def _is_start_command(event: Message | CallbackQuery) -> bool:
    text = getattr(event, "text", None)
    return isinstance(event, Message) and bool(text) and event.text.startswith("/start")

def _is_contact_message(event: Message | CallbackQuery) -> bool:
    return isinstance(event, Message) and event.contact is not None