from __future__ import annotations

import sys
import asyncio
import logging

from aiogram.client.default import DefaultBotProperties
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
#from aiogram.fsm.storage.redis import RedisStorage

from config import settings
from db.database import get_session_factory
from db.bootstrap import init_db_or_fail, shutdown_db
from app.container import build_services
from app.routers import register_routers
from app.middlewares_setup import register_middlewares

logger = logging.getLogger(__name__)


async def build_app() -> tuple[Bot, Dispatcher]:
    """ Composition root:
    - initializes DB (fail-fast)
    - создаём Bot/Dispatcher
    - подключаем routers/middlewares
    - собираем services и настраиваем DI
    """

    # Инициализация базы данных (Postgres-only: если БД недоступна — выходим сразу)
    await init_db_or_fail()

    bot = Bot(
        token=settings.token_value,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())
    #dp = Dispatcher(storage=RedisStorage.from_url(settings.redis_url))

    # Подключаем роутеры
    register_routers(dp)

    # Сессия для репозиториев
    session_factory = get_session_factory()

    # создаём сервисы
    services = build_services(bot=bot, session_factory=session_factory)

    # Middlewares
    register_middlewares(dp=dp, services=services, admin_ids=settings.admin_ids)

    logger.info("Bot is ready")
    return bot, dp

async def main():
    """Запуск aiogram-бота"""

    # Логирование
    logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",level=logging.INFO)

    bot: Bot | None = None
    try:
        # Создаём бота
        bot, dp = await build_app()
        # Запуск
        await dp.start_polling(bot) # , allowed_updates=Update.ALL_TYPES
        logger.info("Бот запущен")
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("Бот остановлен пользователем 🛑")
    except Exception:
        logger.error(f"Ошибка при запуске бота")
        raise
    finally:
        # 1) закрываем bot session
        if bot is not None:
            try:
                await bot.session.close()
            except Exception:
                logger.exception("Failed to close bot session")

        # 2) закрываем DB engine
        try:
            await shutdown_db()
        except Exception:
            logger.exception("Failed to shutdown database")

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except Exception:
        sys.exit(1)