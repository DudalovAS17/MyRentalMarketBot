
PAGE_SIZE = 8
QUERY_MIN_LEN = 2
QUERY_MAX_LEN = 60

@search_router.callback_query(F.data == "search_all")
async def search_in_all_categories(callback: CallbackQuery, state: FSMContext):
    """Поиск по всем категориям.
    Показываем популярные объявления из разных категорий"""

async def _prompt_search_query(event: Message | CallbackQuery, state: FSMContext) -> None:
    await state.set_state(SearchStates.query)
    await state.update_data(search_query=None, search_page=1)
    text = "🔎 Введите текст запроса (2–60 символов)."
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main_menu")]
        ]
    )
    await send_or_edit(event, text, markup=keyboard, parse_mode="HTML")

async def _render_search_results(
    event: Message | CallbackQuery,
    state: FSMContext,
    item_service: ItemService,
    *,
    page: int,
) -> None:
    data = await state.get_data()
    query = (data.get("search_query") or "").strip()
    if not query:
        await _prompt_search_query(event, state)
        return

    safe_page = max(page, 1)
    offset = (safe_page - 1) * PAGE_SIZE
    items = await item_service.search(
        query,
        available_only=True,
        limit=PAGE_SIZE + 1,
        offset=offset,
    )
    has_next = len(items) > PAGE_SIZE
    items = items[:PAGE_SIZE]
    has_prev = safe_page > 1

    await state.update_data(search_page=safe_page)

    if items:
        lines = []
        for index, item in enumerate(items, start=offset + 1):
            title = item.title or "Без названия"
            price = format_price(item.price)
            lines.append(f"{index}. #{item.id} — {title} ({price} ₽/день)")
        results_text = "\n".join(lines)
        text = (
            "🔎 <b>Результаты поиска</b>\n"
            f"Запрос: <code>{query}</code>\n"
            f"Страница {safe_page}\n\n"
            f"{results_text}"
        )
    else:
        text = (
            "🔎 <b>Результаты поиска</b>\n"
            f"Запрос: <code>{query}</code>\n\n"
            "По вашему запросу ничего не найдено."
        )

    keyboard: list[list[InlineKeyboardButton]] = []
    for item in items:
        keyboard.append(
            [InlineKeyboardButton(text=f"🔎 Открыть #{item.id}", callback_data=f"show_item_details:{item.id}")]
        )
    nav_row: list[InlineKeyboardButton] = []
    if has_prev:
        nav_row.append(InlineKeyboardButton(text="⬅️ Пред", callback_data=f"search:page:{safe_page - 1}"))
    if has_next:
        nav_row.append(InlineKeyboardButton(text="➡️ След", callback_data=f"search:page:{safe_page + 1}"))
    if nav_row:
        keyboard.append(nav_row)

    keyboard.append([InlineKeyboardButton(text="✏️ Новый запрос", callback_data="search:new_query")])
    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main_menu")])
    await send_or_edit(event, text, markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")

@search_router.message(Command("search"))
async def start_search_command(message: Message, state: FSMContext) -> None:
    await _prompt_search_query(message, state)

@search_router.message(F.text == "🔎 Поиск")
async def start_search_from_menu(message: Message, state: FSMContext) -> None:
    await _prompt_search_query(message, state)

@search_router.callback_query(F.data == "search:new_query")
async def search_new_query(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await _prompt_search_query(callback, state)

@search_router.callback_query(F.data.startswith("search:page:"))
async def search_paginate(
    callback: CallbackQuery,
    state: FSMContext,
    item_service: ItemService,
) -> None:
    await callback.answer()
    try:
        page = int(callback.data.split(":")[-1])
    except (IndexError, ValueError):
        logger.warning("Invalid pagination callback: %s", callback.data)
        await _prompt_search_query(callback, state)
        return

    await _render_search_results(callback, state, item_service, page=page)

    @search_router.message(SearchStates.query)
    async def handle_search_query(
            message: Message,
            state: FSMContext,
            item_service: ItemService,
    ) -> None:
        query = (message.text or "").strip()
        if not (QUERY_MIN_LEN <= len(query) <= QUERY_MAX_LEN):
            await message.answer("⚠️ Запрос должен быть длиной 2–60 символов. Попробуйте ещё раз.")
            return

        await state.update_data(search_query=query, search_page=1)
        await _render_search_results(message, state, item_service, page=1)


"""
from typing import Dict, Any, List, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, ConversationHandler

from services.item_service import ItemService
from utils.helpers import format_price
from constants import MAIN_MENU, SEARCH_RESULTS, ITEM_DETAILS, RENT_DATES



def search_items(update: Update, context: CallbackContext) -> int:
    ""Обрабатывает запрос поиска товаров""
    if update.message:
        query = update.message.text.strip()

        # Если это команда /search, запрашиваем поисковый запрос
        if query == "/search":
            update.message.reply_text(
                "🔍 *Поиск объявлений*\n\n"
                "Введите ключевые слова для поиска вещей по названию или описанию:",
                parse_mode="Markdown"
            )
            return SEARCH_RESULTS

        # Выполняем поиск
        try:
            items = ItemService.search_items(query)
            return show_search_results(update, context, items, query)
        except Exception as e:
            logger.error(f"Ошибка при поиске объявлений: {e}")
            update.message.reply_text(
                "❌ Произошла ошибка при поиске. Пожалуйста, попробуйте позже."
            )

            # Возвращаемся в главное меню
            from handlers.base import show_main_menu
            return show_main_menu(update, context)
    else:
        # Обработка callback запроса (если был)
        return process_search_callback(update, context)


def show_search_results(update: Update, context: CallbackContext, items: List[Dict[str, Any]], query: str) -> int:
    ""Показывает результаты поиска""
    if not items:
        # Ничего не найдено
        keyboard = [
            [InlineKeyboardButton("🔄 Новый поиск", callback_data="new_search")],
            [InlineKeyboardButton("🔙 Назад в меню", callback_data="back_to_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        update.message.reply_text(
            f"🔍 *Поиск: {query}*\n\n"
            "По вашему запросу ничего не найдено.\n"
            "Попробуйте изменить поисковый запрос или просмотреть категории.",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    else:
        # Найдены объявления
        keyboard = []

        # Добавляем кнопки для каждого объявления
        for item in items[:10]:  # Ограничиваем до 10 результатов
            price_text = format_price(item.get('price_per_day', 0))
            keyboard.append([
                InlineKeyboardButton(
                    f"{item.get('title')} - {price_text}/день",
                    callback_data=f"view_item:{item.get('id')}"
                )
            ])

        # Кнопки для навигации
        nav_buttons = []

        if len(items) > 10:
            nav_buttons.append(
                InlineKeyboardButton("➡️ Следующие", callback_data="next_page:1")
            )

        # Добавляем кнопки для нового поиска и возврата в меню
        keyboard.append([InlineKeyboardButton("🔄 Новый поиск", callback_data="new_search")])
        keyboard.append([InlineKeyboardButton("🔙 Назад в меню", callback_data="back_to_menu")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        message_text = (
            f"🔍 *Результаты поиска: {query}*\n\n"
            f"Найдено {len(items)} объявлений. Выберите объявление для просмотра:"
        )

        # Сохраняем результаты поиска и запрос в контексте для пагинации
        context.user_data["search_results"] = items
        context.user_data["search_query"] = query
        context.user_data["search_page"] = 0

        update.message.reply_text(
            message_text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

    return SEARCH_RESULTS


def process_search_callback(update: Update, context: CallbackContext) -> int:
    ""Обрабатывает callback-запросы в разделе поиска""
    query = update.callback_query
    callback_data = query.data

    if callback_data == "new_search":
        # Запрашиваем новый поисковый запрос
        query.message.reply_text(
            "🔍 *Новый поиск*\n\n"
            "Введите ключевые слова для поиска вещей по названию или описанию:",
            parse_mode="Markdown"
        )
        query.answer()
        return SEARCH_RESULTS

    elif callback_data == "back_to_menu":
        # Возвращаемся в главное меню
        from handlers.base import show_main_menu
        query.answer()
        return show_main_menu(update, context)

    elif callback_data.startswith("next_page:") or callback_data.startswith("prev_page:"):
        # Обрабатываем пагинацию результатов
        page = int(callback_data.split(":")[1])
        items = context.user_data.get("search_results", [])
        query_text = context.user_data.get("search_query", "")

        # Обновляем текущую страницу
        context.user_data["search_page"] = page

        start_idx = page * 10
        end_idx = min(start_idx + 10, len(items))

        keyboard = []

        # Добавляем кнопки для объявлений текущей страницы
        for item in items[start_idx:end_idx]:
            price_text = format_price(item.get('price_per_day', 0))
            keyboard.append([
                InlineKeyboardButton(
                    f"{item.get('title')} - {price_text}/день",
                    callback_data=f"view_item:{item.get('id')}"
                )
            ])

        # Кнопки для навигации
        nav_buttons = []

        if page > 0:
            nav_buttons.append(
                InlineKeyboardButton("⬅️ Предыдущие", callback_data=f"prev_page:{page - 1}")
            )

        if end_idx < len(items):
            nav_buttons.append(
                InlineKeyboardButton("➡️ Следующие", callback_data=f"next_page:{page + 1}")
            )

        if nav_buttons:
            keyboard.append(nav_buttons)

        # Добавляем кнопки для нового поиска и возврата в меню
        keyboard.append([InlineKeyboardButton("🔄 Новый поиск", callback_data="new_search")])
        keyboard.append([InlineKeyboardButton("🔙 Назад в меню", callback_data="back_to_menu")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        message_text = (
            f"🔍 *Результаты поиска: {query_text}*\n\n"
            f"Найдено {len(items)} объявлений. Страница {page + 1} из {(len(items) - 1) // 10 + 1}."
            f" Выберите объявление для просмотра:"
        )

        query.edit_message_text(
            message_text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        query.answer()

        return SEARCH_RESULTS

    elif callback_data.startswith("view_item:"):
        # Переходим к просмотру выбранного объявления
        item_id = callback_data.split(":")[1]
        return show_item_details(update, context, item_id)

    # По умолчанию возвращаемся в начало поиска
    query.answer()
    return SEARCH_RESULTS


def show_item_details(update: Update, context: CallbackContext, item_id: str) -> int:
    ""Показывает детальную информацию о выбранном объявлении""
    query = update.callback_query

    try:
        # Получаем данные объявления
        item = ItemService.get_item_by_id(item_id)

        if not item:
            query.answer("❌ Объявление не найдено или было удалено")
            return SEARCH_RESULTS

        # Сохраняем ID объявления в контексте
        context.user_data["selected_item_id"] = item_id

        # Форматируем информацию об объявлении
        item_details = (
            f"📦 *{item.get('title')}*\n\n"
            f"📝 {item.get('description')}\n\n"
            f"💰 *Цена аренды:* {format_price(item.get('price_per_day'))} / день\n"
            f"🔐 *Залог:* {format_price(item.get('deposit_amount'))}\n"
            f"⏱️ *Мин. срок аренды:* {item.get('min_rental_period')}\n"
            f"📍 *Местоположение:* {item.get('location')}\n\n"
            f"👤 *Владелец:* {item.get('owner_name')}\n"
            f"⭐ *Рейтинг:* {item.get('owner_rating', '5.0')}/5.0\n"
            f"📅 *Дата публикации:* {item.get('created_at')}"
        )

        # Кнопки для аренды и возврата
        keyboard = [
            [InlineKeyboardButton("🤝 Арендовать", callback_data=f"rent_item:{item_id}")],
            [InlineKeyboardButton("🔙 Назад к результатам", callback_data="back_to_results")],
            [InlineKeyboardButton("🏠 В главное меню", callback_data="back_to_menu")]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        # Отображаем информацию
        if item.get('photo_url'):
            query.edit_message_caption(
                caption=item_details,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        else:
            query.edit_message_text(
                item_details,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )

        query.answer()
        return ITEM_DETAILS

    except Exception as e:
        logger.error(f"Ошибка при отображении объявления {item_id}: {e}")
        query.answer("❌ Произошла ошибка при загрузке объявления")
        return SEARCH_RESULTS


def process_item_details_callback(update: Update, context: CallbackContext) -> int:
    ""Обрабатывает действия с детальной страницы объявления""
    query = update.callback_query
    callback_data = query.data

    if callback_data == "back_to_results":
        # Возвращаемся к результатам поиска
        query.answer()

        items = context.user_data.get("search_results", [])
        query_text = context.user_data.get("search_query", "")
        page = context.user_data.get("search_page", 0)

        if not items:
            # Если нет результатов поиска, возвращаемся в меню
            from handlers.base import show_main_menu
            return show_main_menu(update, context)

        # Перестраиваем результаты поиска
        start_idx = page * 10
        end_idx = min(start_idx + 10, len(items))

        keyboard = []

        # Добавляем кнопки для объявлений текущей страницы
        for item in items[start_idx:end_idx]:
            price_text = format_price(item.get('price_per_day', 0))
            keyboard.append([
                InlineKeyboardButton(
                    f"{item.get('title')} - {price_text}/день",
                    callback_data=f"view_item:{item.get('id')}"
                )
            ])

        # Кнопки для навигации
        nav_buttons = []

        if page > 0:
            nav_buttons.append(
                InlineKeyboardButton("⬅️ Предыдущие", callback_data=f"prev_page:{page - 1}")
            )

        if end_idx < len(items):
            nav_buttons.append(
                InlineKeyboardButton("➡️ Следующие", callback_data=f"next_page:{page + 1}")
            )

        if nav_buttons:
            keyboard.append(nav_buttons)

        # Добавляем кнопки для нового поиска и возврата в меню
        keyboard.append([InlineKeyboardButton("🔄 Новый поиск", callback_data="new_search")])
        keyboard.append([InlineKeyboardButton("🔙 Назад в меню", callback_data="back_to_menu")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        message_text = (
            f"🔍 *Результаты поиска: {query_text}*\n\n"
            f"Найдено {len(items)} объявлений. Страница {page + 1} из {(len(items) - 1) // 10 + 1}."
            f" Выберите объявление для просмотра:"
        )

        query.edit_message_text(
            message_text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

        return SEARCH_RESULTS

    elif callback_data.startswith("rent_item:"):
        # Переходим к аренде выбранного объявления
        item_id = callback_data.split(":")[1]
        return rent_item(update, context, item_id)

    elif callback_data == "back_to_menu":
        # Возвращаемся в главное меню
        from handlers.base import show_main_menu
        query.answer()
        return show_main_menu(update, context)

    # По умолчанию возвращаемся к деталям объявления
    query.answer()
    return ITEM_DETAILS


def rent_item(update: Update, context: CallbackContext, item_id: str) -> int:
    ""Начинает процесс аренды выбранного объявления""
    query = update.callback_query

    try:
        # Получаем данные объявления
        item = ItemService.get_item_by_id(item_id)

        if not item:
            query.answer("❌ Объявление не найдено или было удалено")
            return SEARCH_RESULTS

        # Сохраняем данные о выбранном объявлении
        context.user_data["rent_item"] = {
            "item_id": item_id,
            "item_title": item.get("title"),
            "price_per_day": item.get("price_per_day"),
            "deposit": item.get("deposit_amount")
        }

        # Запрашиваем даты аренды
        message_text = (
            f"📅 *Аренда: {item.get('title')}*\n\n"
            f"Пожалуйста, укажите желаемые даты аренды в формате ДД.ММ.ГГГГ-ДД.ММ.ГГГГ\n"
            f"Например: 01.06.2023-05.06.2023\n\n"
            f"Минимальный срок аренды: {item.get('min_rental_period')}\n"
            f"Стоимость: {format_price(item.get('price_per_day'))} / день\n"
            f"Залог: {format_price(item.get('deposit_amount'))}"
        )

        keyboard = [
            [InlineKeyboardButton("🔙 Отмена", callback_data="cancel_rent")]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        query.edit_message_text(
            message_text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

        query.answer()
        return RENT_DATES

    except Exception as e:
        logger.error(f"Ошибка при начале аренды объявления {item_id}: {e}")
        query.answer("❌ Произошла ошибка при обработке запроса")
        return ITEM_DETAILS

"""



















































































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