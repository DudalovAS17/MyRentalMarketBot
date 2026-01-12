from aiogram import BaseMiddleware
from typing import Callable, Dict, Any, Awaitable

class ServicesMiddleware(BaseMiddleware):
    def __init__(self, **services):
        # сюда кладём все сервисы при инициализации
        self.services = services

    async def __call__(
        self,
        handler: Callable[[Dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: Dict[str, Any]
    ) -> Any:
        # добавляем сервисы в data, чтобы aiogram мог подставить их в хендлеры
        data.update(self.services)
        # Теперь data = {"event_from_user": User(...), "state": FSMContext(...),
        # "user_service": <UserService>, "category_service": <CategoryService>}
        return await handler(event, data)

"""Aiogram смотрит на аргументы твоего хендлера:
async def rent_button_handler(message: Message, category_service: CategoryService) -
Видит category_service и подставляет его из data.


ServicesMiddleware кладёт все твои сервисы в data. Aiogram сам «инжектит» их в аргументы хендлеров.
"""