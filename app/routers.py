from __future__ import annotations

from aiogram import Dispatcher

from handlers.admin import admin_router
from handlers.auth import auth_router
from handlers.base import base_router
from handlers.category import category_router
from handlers.item.router import items_router
from handlers.rentals.router import rental_router
from handlers.search import search_router
from handlers.support import support_router


def register_routers(dp: Dispatcher) -> None:
    # Подключаем роутеры, порядок важен: конкретные роутеры раньше, базовый catch-all — последним

    # 1) Самые конкретные FSM/сценарии
    dp.include_router(items_router)
    dp.include_router(category_router)
    dp.include_router(rental_router)

    # 2) Профиль/регистрация
    dp.include_router(auth_router)

    # 3) Поиск/прочие
    dp.include_router(search_router)

    # 4) Админка (достаточно конкретная, и её нельзя отдавать базовому “catch-all”)
    dp.include_router(admin_router)

    # 5) Поддержка
    dp.include_router(support_router)

    # 6) Базовый роутер — строго последним
    dp.include_router(base_router)
