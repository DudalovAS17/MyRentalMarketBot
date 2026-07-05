from __future__ import annotations

import sys
import asyncio
import logging
from contextlib import suppress

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

# ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
async def build_app() -> tuple[Bot, Dispatcher]:
    """ Composition root приложения. Делает всю startup-сборку"""

    # Инициализация базы данных (Postgres-only: если БД недоступна — выходим сразу)
    await init_db_or_fail()

    # Создать Telegram Bot
    bot = Bot(
        token=settings.token_value,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    try:
        # Создать Dispatcher
        dp = Dispatcher(storage=MemoryStorage()) # =RedisStorage.from_url(settings.redis_url)

        # Подключаем роутеры
        register_routers(dp)

        # Сессия для репозиториев
        session_factory = get_session_factory()

        # создаём сервисы
        services = build_services(bot=bot, session_factory=session_factory)

        # Bootstrap доменных профилей админов из ADMIN_IDS: доступ по-прежнему проверяется whitelist middleware.
        await services.admin_directory_service.sync_admins_from_settings(settings.admin_ids)

        # Middlewares
        register_middlewares(dp=dp, services=services, admin_ids=settings.admin_ids)

        logger.info("Application build completed")
        return bot, dp

    except Exception:
        # Если ошибка случилась после создания Bot, но до возврата из build_app(), main() ещё не получил bot и не сможет закрыть session самостоятельно.
        with suppress(Exception):
            await bot.session.close()
        raise

# ────────────────────────────────────────────── helpers for main ──────────────────────────────────────────────────────
def configure_logging() -> None:
    """Настроить базовое логирование приложения."""
    logging.basicConfig(
        level=settings.log_level_value,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        force=True,
    )

async def close_bot_session(bot: Bot | None) -> None:
    """Безопасно закрыть HTTP-сессию Telegram Bot (закрываем bot session)"""
    if bot is None:
        return

    # noinspection PyBroadException
    try:
        await bot.session.close()
        logger.info("Bot session closed")
    except Exception:
        logger.exception("Failed to close bot session")

async def shutdown_application(bot: Bot | None) -> None:
    """Graceful shutdown приложения (закрываем DB engine)"""
    await close_bot_session(bot)

    # noinspection PyBroadException
    try:
        await shutdown_db()
        logger.info("Database engine disposed")
    except Exception:
        logger.exception("Failed to shutdown database")

# ─────────────────────────────────────────────────── main ─────────────────────────────────────────────────────────────
async def main():
    """Запустить Telegram-бота в polling-режиме."""

    # Логирование
    configure_logging()
    settings.log_startup_warnings()

    bot: Bot | None = None

    try:
        # Создаём бота
        bot, dp = await build_app()

        logger.info("Starting bot polling")
        await bot.delete_webhook(drop_pending_updates=settings.drop_pending_updates)
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types() # , allowed_updates=Update.ALL_TYPES
        )
        logger.info("Bot polling stopped")

    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("Бот остановлен пользователем 🛑")
    except Exception:
        logger.exception("Ошибка при запуске бота")
        raise

    finally:
        await shutdown_application(bot)

if __name__ == '__main__':
    # noinspection PyBroadException
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception:
        sys.exit(1)