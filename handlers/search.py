import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext

# Импортируем свои константы (пути назад и т.п.)
#from keyboards.constants import BACK_CB

logger = logging.getLogger(__name__)

search_router = Router()  # <-- подключим в main.py

@search_router.callback_query(F.data == "search_all")
async def search_in_all_categories(callback: CallbackQuery, state: FSMContext):
    """Поиск по всем категориям.
    Показываем популярные объявления из разных категорий"""


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
