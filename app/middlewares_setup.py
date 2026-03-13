from __future__ import annotations

from aiogram import Dispatcher

from handlers.admin import admin_router
from middlewares.admin_check import AdminCheckMiddleware
from middlewares.error_handler import GlobalErrorMiddleware
from middlewares.registration_check import RegistrationCheckMiddleware
from middlewares.services import ServicesMiddleware

from app.container import AppServices


def register_middlewares(*, dp: Dispatcher, services: AppServices, admin_ids: set[int]) -> None:
    # 1) Global Error Middleware - на самом верху (должен ловить все!)
    dp.message.middleware(GlobalErrorMiddleware())
    dp.callback_query.middleware(GlobalErrorMiddleware())

    # 2) DI middleware: единственный источник сервисов для handler injection
    di = ServicesMiddleware(
        user_service=services.user_service,
        category_service=services.category_service,
        item_service=services.item_service,
        rental_service=services.rental_service,
        photo_service=services.photo_service,
        review_service=services.review_service,
        admin_service=services.admin_service, # нужны тут?
        admin_rental_service=services.admin_rental_service, # нужны тут?
        support_service=services.support_service,
        notification_service=services.notification_service,
        admin_ids=admin_ids, # ?
    )
    dp.message.middleware(di)
    dp.callback_query.middleware(di)

    admin_ids = frozenset(admin_ids)  # ✅ защищаем от случайной мутации

    # 3) Global registration guard (middleware регистрации — проверяет доступ)
    reg = RegistrationCheckMiddleware(services.user_service, admin_ids=admin_ids)
    # RegistrationCheckMiddleware — глобальный: пусть проверяет регистрацию/блокировку везде
    dp.message.middleware(reg)
    dp.callback_query.middleware(reg)

    # 4) Admin guard only for admin router
    admin_guard = AdminCheckMiddleware(admin_ids)
    # AdminCheckMiddleware — точечный: проверяет админство только в админских хендлерах
    admin_router.message.middleware(admin_guard)
    admin_router.callback_query.middleware(admin_guard)



