from aiogram import BaseMiddleware
from typing import Callable, Any, Awaitable
from aiogram.types import Message, CallbackQuery


class ServicesMiddleware(BaseMiddleware):
    """Middleware, который добавляет заранее собранные сервисы в `data` для передачи в хендлеры"""

    def __init__(self, **services):
        # сюда кладём все сервисы при инициализации
        self.services = services

    async def __call__(self,
                       handler: Callable[[Message | CallbackQuery, dict[str, Any]], Awaitable[Any]],
                       event: Message | CallbackQuery,
                       data: dict[str, Any]
                       ) -> Any:

        data.update(self.services)

        return await handler(event, data)
