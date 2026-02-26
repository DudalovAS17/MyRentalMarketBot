# main.py (aiogram v3)
import asyncio
import logging
import sys

from aiogram.client.default import DefaultBotProperties
from aiogram import Bot, Dispatcher #, F
from aiogram.enums import ParseMode
# from aiogram.types import Update
from aiogram.fsm.storage.memory import MemoryStorage  # или RedisStorage
# from aiogram.fsm.storage.redis import RedisStorage

from config import TELEGRAM_TOKEN
from db.database import init_db, check_db_connection, get_session_factory

from db.repositories.user import UserRepository
from db.repositories.category import CategoryRepository
from db.repositories.item import ItemRepository
from db.repositories.rental import RentalRepository
from db.repositories.photo import PhotoRepository
from db.repositories.admin import AdminActionRepository
from db.repositories.review import ReviewRepository
from db.repositories.support_ticket import SupportTicketRepository

from services.user_service import UserService
from services.category_service import CategoryService
from services.item_service import ItemService
from services.rental_service import RentalService
from services.photo_service import PhotoService
from services.review_service import ReviewService
from services.admin_service import AdminActionService
from services.admin_rental_service import AdminRentalService
from services.support_service import SupportService
from services.notif_service import NotificationService

from handlers.base import base_router
from handlers.category import category_router
from handlers.auth import auth_router
from handlers.item import items_router
from handlers.rental import rental_router
from handlers.search import search_router
from handlers.admin import admin_router
from handlers.support import support_router

from middlewares.services import ServicesMiddleware
from middlewares.registration_check import RegistrationCheckMiddleware
from middlewares.admin_check import AdminCheckMiddleware
from middlewares.error_handler import GlobalErrorMiddleware

from config import ADMIN_IDS

logger = logging.getLogger(__name__)


async def main():
    """Запуск aiogram-бота"""

    # Логирование
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO
    )

    # Инициализация базы данных
    try:
        # ✅ Проверяем подключение к БД
        if await check_db_connection():
            await init_db(create_tables=False)
            logger.info("База данных успешно инициализирована")
        else:
            logger.error("Не удалось подключиться к базе данных")
            return
    except Exception as e:
        logger.error(f"Ошибка инициализации базы данных: {e}", exc_info=True)
        logger.warning("Бот запускается без БД (ограниченный функционал)")


    if not TELEGRAM_TOKEN:
        logger.error("Токен не найден в конфиге")
        sys.exit(1)

    # Создаём бота
    bot = Bot(
        token=TELEGRAM_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Подключаем роутеры
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

    # Сессия для репозиториев
    session_factory = get_session_factory()

    # repositories
    user_repo = UserRepository(session_factory)
    item_repo = ItemRepository(session_factory)
    rental_repo = RentalRepository(session_factory)
    category_repo = CategoryRepository(session_factory)
    photo_repo = PhotoRepository(session_factory)
    review_repo = ReviewRepository(session_factory)
    admin_repo = AdminActionRepository(session_factory)
    support_repo = SupportTicketRepository(session_factory)

    # создаём сервисы
    user_service = UserService(user_repo)
    item_service = ItemService(item_repo, photo_repo, rental_repo)
    notification_service = NotificationService(bot)
    rental_service = RentalService(rental_repo) # , item_service, user_service, notification_service
    category_service = CategoryService(category_repo)
    photo_service = PhotoService(photo_repo)
    review_service = ReviewService(review_repo, rental_repo, user_repo)
    admin_service = AdminActionService(admin_repo)
    admin_rental_service = AdminRentalService(rental_repo, admin_service) # item_service, user_service,
    support_service = SupportService(support_repo)


    # DI: сохраняем сервисы в контексте dp
    dp["user_service"] = user_service
    dp["category_service"] = category_service
    dp["item_service"] = item_service
    dp["rental_service"] = rental_service
    dp["photo_service"] = photo_service
    dp["review_service"] = review_service
    dp["admin_service"] = admin_service
    dp["admin_rental_service"] = admin_rental_service
    dp["support_service"] = support_service
    dp["notification_service"] = notification_service

    admin_ids = ADMIN_IDS

    # Global Error Middleware - на самом верху (должен ловить все!)
    dp.message.middleware(GlobalErrorMiddleware())
    dp.callback_query.middleware(GlobalErrorMiddleware())

    # Подключаем DI-middleware — добавляет все сервисы
    dp.message.middleware(ServicesMiddleware(
        user_service=user_service,
        category_service=category_service,
        item_service=item_service,
        rental_service=rental_service,
        photo_service=photo_service,
        review_service=review_service,
        admin_service=admin_service, # нужны тут?
        admin_rental_service=admin_rental_service, # нужны тут?
        support_service=support_service,
        notification_service=notification_service,
        admin_ids=admin_ids,
    ))
    dp.callback_query.middleware(ServicesMiddleware(
        user_service=user_service,
        category_service=category_service,
        item_service=item_service,
        rental_service=rental_service,
        photo_service=photo_service,
        review_service=review_service,
        admin_service=admin_service, # нужны тут?
        admin_rental_service=admin_rental_service, # нужны тут?
        support_service=support_service,
        notification_service=notification_service,
        admin_ids=admin_ids,
    ))

    # Подключаем middleware регистрации — проверяет доступ
    dp.message.middleware(RegistrationCheckMiddleware(user_service))
    dp.callback_query.middleware(RegistrationCheckMiddleware(user_service))
    # RegistrationCheckMiddleware — глобальный: пусть проверяет регистрацию/блокировку везде

    admin_router.message.middleware(AdminCheckMiddleware(admin_ids))
    admin_router.callback_query.middleware(AdminCheckMiddleware(admin_ids))
    # AdminCheckMiddleware — точечный: проверяет админство только в админских хендлерах

    # Запуск
    logger.info("Бот запущен")
    try:
        await dp.start_polling(bot) # , allowed_updates=Update.ALL_TYPES
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("Бот остановлен пользователем 🛑")
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())
