import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

from utils.errors import ServiceError

logger = logging.getLogger(__name__)

# Пока не актуальный - не понимаю что и зачем

""" Каноничный Global Error Middleware (aiogram 3)

- Централизованный перехват только неожиданных/технических ошибок
- Stacktrace логируется один раз (exc_info=True / logger.exception)
- Пользователю отправляем нейтральный ответ:
       - Message -> answer()
       - CallbackQuery -> answer(show_alert=True)
- business errors (ServiceError) тут НЕ ловим (их ловят handlers) - НЕ содержит бизнес-логики

- Исключение НЕ пробрасываем дальше (иначе будет дубль логов / падение) - ?
"""

class GlobalErrorMiddleware(BaseMiddleware):
    """Единый обработчик технических ошибок (глобальный): лог + безопасный ответ пользователю"""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any], # Dict
    ) -> Any:
        try:
            return await handler(event, data)

        # Бизнес-ошибки не трогаем: они должны обрабатываться в handlers.
        except ServiceError:
            raise

        # Технические ошибки: логируем один раз + нейтральный UX
        except Exception as exc:
            # Техническая ошибка -> лог со stacktrace
            #logger.error("Глобальная техническая ошибка: %s", exc, exc_info=True)
            # как я понял exception = error + exc_info=True - компактней
            logger.exception("Unhandled техническая ошибка: %s", exc)

            # ответ пользователю (не раскрываем детали)
            try:
                if isinstance(event, Message):
                    await event.answer("⚠️ Технический сбой. Попробуйте позже.")
                elif isinstance(event, CallbackQuery):
                    await event.answer("⚠️ Технический сбой. Попробуйте позже.", show_alert=True)
                else:
                    # Если тип события неизвестен — молча ничего не отвечаем
                    pass
            except Exception as send_exc:
                # Если даже ответ пользователю не смогли отправить — логируем, но не падаем повторно
                #logger.error("Не удалось отправить сообщение о сбое: %s", send_exc, exc_info=True)
                logger.exception("Не удалось отправить сообщение о сбое: %s", send_exc)

            # Прерываем цепочку: хендлер не должен продолжаться
            # ВАЖНО: НЕ пробрасываем исключение дальше — иначе будет дубль и падение.
            return None


"""
1) SQLAlchemyError - Ловим тут!

except SQLAlchemyError as e:
    logger.error(" [Start] Ошибка БД при регистрации %s: %s", telegram_id, e)
    await message.answer(
        "❌ Произошла ошибка при подключении к базе данных. Попробуйте позже."
    )
    return

Это уже:
    ошибки БД,
    инфраструктура,
    технический сбой,
    не бизнес-логика.

2) IntegrityError - НЕ ловим тут!

except IntegrityError:
    await message.answer("⚠️ Вы уже зарегистрированы. Используйте /start для входа в меню.")
    return
    
Обычно это значит:
    нарушение unique constraint;
    у вас уже есть пользователь с таким telegram_id

Это ожидаемый сценарий гонки/повторного входа:
    юзер уже существует;
    повторно вызвали регистрацию;
    БД защитила от дубля.
    
3) Exception - Ловим тут!

except Exception as e:
    logger.exception("Неожиданная ошибка при регистрации %s", telegram_id)
    # logger.error(f"Ошибка при регистрации пользователя {telegram_id}: {e}", exc_info=True)
    await message.answer("⚠️ Произошла внутренняя ошибка. Попробуйте позже.")
    return

Что это значит
Это catch-all:
    любые неожиданные ошибки,
    программные баги,
    неожиданные падения.
    
4) RuntimeError - Ловим тут!

5) TelegramAPIError - ?

except TelegramAPIError as e:
    logger.error(f"[Start] Ошибка Telegram API: {e}")
    return await message.answer("⚠️ Ошибка при связи с Telegram. Повторите позже.")

Это ошибки при обращении к Telegram API, например:
    сообщение нельзя отправить;
    сообщение нельзя отредактировать;
    чат недоступен;
    объект сообщения уже удалён;
    
    
"""