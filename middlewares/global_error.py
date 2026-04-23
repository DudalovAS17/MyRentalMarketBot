import logging
from typing import Any, Awaitable, Callable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

from utils.errors import ServiceError
from texts.text_middleware import err_for_msg, err_for_callback

logger = logging.getLogger(__name__)

class GlobalErrorMiddleware(BaseMiddleware):
    """Единый обработчик технических ошибок (глобальный): лог + безопасный ответ пользователю"""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:

        try:
            return await handler(event, data)

        # Бизнес-ошибки не трогаем
        except ServiceError:
            raise

        # Технические ошибки
        except Exception as exc:
            logger.exception("Unhandled техническая ошибка: %s", exc)

            # ответ пользователю (не раскрываем детали)
            try:
                if isinstance(event, Message):
                    await event.answer(err_for_msg)
                elif isinstance(event, CallbackQuery):
                    await event.answer(err_for_callback, show_alert=True)
                else:
                    pass # Если тип события неизвестен — молча ничего не отвечаем
            except Exception as send_exc:
                # Если даже ответ пользователю не смогли отправить — логируем, но не падаем повторно
                logger.exception("Не удалось отправить сообщение о сбое: %s", send_exc)

            # Прерываем цепочку: хендлер не должен продолжаться
            # ВАЖНО: НЕ пробрасываем исключение дальше — иначе будет дубль и падение.
            return None