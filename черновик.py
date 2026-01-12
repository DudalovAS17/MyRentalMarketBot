import asyncio
import logging
import os
import sys
import importlib
from typing import List

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
# 8417386001:AAFnNXYWItg0LlbXWyUQVikxo_aOGyhJq0U
# ── Логирование ────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)
8

# ── Конфиг: пытаемся взять старый TELEGRAM_TOKEN, иначе BOT_TOKEN из env ──────
def load_bot_token() -> str:
    token = None
    try:
        # Старый проект: config.TELEGRAM_TOKEN
        from config import TELEGRAM_TOKEN  # type: ignore
        token = TELEGRAM_TOKEN
        if token:
            logger.info("Использую TELEGRAM_TOKEN из config.py")
    except Exception:
        pass

    if not token:
        token = os.getenv("BOT_TOKEN")

    if not token:
        logger.error("Не найден токен бота. Установи TELEGRAM_TOKEN в config.py или BOT_TOKEN в окружении.")
        sys.exit(1)

    return token


# ── Инициализация БД (вызываем синхронный код аккуратно) ──────────────────────
async def init_database_if_possible() -> None:
    """
    Вызывает init_db/check_db_connection из db.database, если они есть.
    Делается через to_thread, чтобы не блокировать event loop.
    """
    try:
        from db.database import init_db, check_db_connection  # type: ignore

        ok = await asyncio.to_thread(check_db_connection)
        if ok:
            await asyncio.to_thread(init_db)
            logger.info("База данных успешно инициализирована.")
        else:
            logger.error("Не удалось подключиться к базе данных. Некоторые функции могут быть недоступны.")
    except Exception as e:
        logger.error(f"Ошибка инициализации базы данных: {e}", exc_info=True)
        logger.warning("Бот запускается без подключения к БД. Некоторые функции могут быть недоступны.")


# ── Подключение роутеров из новых aiogram-модулей ─────────────────────────────
def include_routers(dp: Dispatcher) -> None:
    """
    Подключает aiogram-роутеры, если модули существуют и экспортируют `router`.
    Перенос делаем в каталог `app/handlers/*` (чтобы не конфликтовать со старыми PTB-модулями в `handlers/*`).
    На старте можно оставить список пустым и добавлять по мере миграции.
    """
    modules: List[str] = [
        # добавляй по мере переноса:
        "app.handlers.base",        # перенесённый /start, меню, help, legal и т.д.
        "app.handlers.auth",        # регистрация, профиль, смена телефона (FSM)
        "app.handlers.items",       # создание/редактирование объявлений (FSM)
        "app.handlers.category",    # выбор категорий/подкатегорий
        "app.handlers.search",      # поиск (FSM)
        "app.handlers.rentals",     # сделки/аренды (FSM)
        "app.handlers.reviews",     # отзывы
        "app.handlers.support",     # поддержка
        "app.handlers.admin",       # админка (если есть)
    ]

    connected = 0
    for modname in modules:
        try:
            mod = importlib.import_module(modname)
        except ModuleNotFoundError:
            logger.warning(f"Модуль {modname} не найден (ещё не перенесён) — пропускаю.")
            continue
        except Exception as e:
            logger.error(f"Ошибка импорта {modname}: {e}", exc_info=True)
            continue

        router = getattr(mod, "router", None)
        if router is None:
            logger.warning(f"В модуле {modname} нет `router` — пропускаю.")
            continue

        try:
            dp.include_router(router)
            connected += 1
            logger.info(f"Подключён роутер из {modname}")
        except Exception as e:
            logger.error(f"Не удалось подключить роутер {modname}: {e}", exc_info=True)

    if connected == 0:
        logger.warning("Не подключено ни одного роутера. Бот запустится, но обрабатывать команды не будет.")


# ── Точка входа ────────────────────────────────────────────────────────────────
async def main() -> None:
    token = load_bot_token()

    # Инициализация БД (не блокируем event loop)
    await init_database_if_possible()

    bot = Bot(
        token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Подключаем роутеры (новые aiogram-хендлеры)
    include_routers(dp)

    # Запуск
    logger.info("Бот запускается (aiogram v3)...")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен пользователем.")