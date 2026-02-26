import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from services.item_service import ItemService
from states.search import SearchStates
from keyboards.search_kb import build_search_keyboard
from utils.functions import format_price, send_or_edit

logger = logging.getLogger(__name__)

search_router = Router()

""" Минимальный MVP-поиска.

Сознательно не включили:
❌ фильтры по цене / категории / городу
❌ умная релевантность
❌ сохранённые поиски
❌ история запросов
❌ “похожие объявления”
"""

PAGE_SIZE = 8
QUERY_MIN_LEN = 2
QUERY_MAX_LEN = 60

# update_data: "search_query", "search_page"

def _render_results_text(query: str, items, page: int) -> str:
    header = f"🔍 <b>Поиск:</b> {query}\n"
    header += f"Страница: {page}\n\n"

    if not items:
        return f"{header}""Ничего не найдено. Попробуйте изменить запрос."

    lines = []
    for item in items:
        price = format_price(item.price)
        title = item.title or "Без названия"
        location = f" ({item.location})" if item.location else ""
        #code = f"Запрос: <code>{query}</code>\n\n" - можно добавить
        lines.append(f"• {title} — {price} ₽/день{location}")

    return f"{header}" + "\n".join(lines)

async def _prompt_search_query(event: Message | CallbackQuery, state: FSMContext) -> None:
    # Инвариант: если просим запрос — мы в waiting_for_query и query сброшен
    await state.set_state(SearchStates.waiting_for_query)
    await state.update_data(search_query=None, search_page=1)

    text = "🔎 Введите текст запроса (2–60 символов)."
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="search:back")] # back_to_main_menu
        ]
    )

    await send_or_edit(event, text, markup=keyboard)

async def _fetch_search_page(query: str, page: int, item_service: ItemService):
    safe_page = max(page, 1)
    offset = (safe_page - 1) * PAGE_SIZE
    items = await item_service.search( # Поиск объявлений по тексту
        query,
        available_only=True,
        limit=PAGE_SIZE + 1,
        offset=offset,
    )
    has_next = len(items) > PAGE_SIZE
    return items[:PAGE_SIZE], has_next, safe_page # items[:PAGE_SIZE] - если пришло 9 → показываем первые 8


""" Клава build_search_keyboard:
🔎 Открыть #{item.id} - "show_item_details:{item.id}"
⬅️ Пред - "search:page:{page - 1}"
➡️ След - "search:page:{page + 1}"
✏️ Новый запрос - "search:new_query"
🔙 Назад - "search:back" / "back_to_main_menu"

На будущее:
"back_to_results" -  Возвращаемся к результатам поиска
"""


async def _show_search_results(
    event: Message | CallbackQuery,
    state: FSMContext,
    item_service: ItemService,
    page: int | None = None,
):
    data = await state.get_data()
    query = data.get("search_query")
    if not query:
        return await _prompt_search_query(event, state)

    current_page = page or data.get("search_page", 1)
    items, has_next, safe_page = await _fetch_search_page(query, current_page, item_service)
    await state.update_data(search_page=safe_page)

    text = _render_results_text(query, items, safe_page)
    keyboard = build_search_keyboard(items, safe_page, has_next)
    return await send_or_edit(event, text, markup=keyboard)


@search_router.message(Command("search"))
@search_router.message(F.text == "🔎 Поиск")
async def start_search(message: Message, state: FSMContext):
    await _prompt_search_query(message, state)


@search_router.callback_query(F.data == "search:new_query")
async def request_new_query(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await _prompt_search_query(callback, state)


@search_router.message(SearchStates.waiting_for_query)
async def process_search_query(message: Message, state: FSMContext, item_service: ItemService):
    query = (message.text or "").strip()
    if not (QUERY_MIN_LEN <= len(query) <= QUERY_MAX_LEN):
        await message.answer("Запрос должен быть длиной от 2 до 60 символов. Попробуйте ещё раз.")
        # мы остаемся в том же состоянии FSM-состоянии
        return

    await state.update_data(search_query=query, search_page=1)
    await state.set_state(SearchStates.browsing)
    await _show_search_results(message, state, item_service, page=1)


@search_router.callback_query(F.data.startswith("search:page:"))
async def paginate_search(callback: CallbackQuery, state: FSMContext, item_service: ItemService):
    await callback.answer()
    try:
        next_page = int(callback.data.split(":")[-1])
    except (ValueError, IndexError):
        await _prompt_search_query(callback, state) # точно сюда?
        return

    data = await state.get_data()
    query = data.get("search_query")
    if not query:
        await _prompt_search_query(callback, state)
        return

    await _show_search_results(callback, state, item_service, page=next_page)


""" На будущее """
#@search_router.callback_query(F.data == "search_back")
#async def back_to_search_results(callback: CallbackQuery, state: FSMContext, item_service: ItemService):
#    await callback.answer()
#    await _show_search_results(callback, state, item_service)


# @search_router.callback_query(F.data == "search_all")
# async def search_in_all_categories(callback: CallbackQuery, state: FSMContext):
#     """Поиск по всем категориям.
#     Показываем популярные объявления из разных категорий"""


"""
SEARCH_CITY_CB = "search_by_city"
SEARCH_FILTERS_CB = "search_filters"

     ALL_CATEGORY_CB: Поиску по всем категориям - search_in_all_categories() - ALL_CATEGORY_CB
 
    "search_by_name": Выбран поиск по названию - search_by_name()

    "search_by_city": Выбран поиск по городу - process_search_by_city() - SEARCH_CITY_CB

    "search_filters": Выбраны фильтры поиска - process_search_filters() - SEARCH_FILTERS_CB

    Поиск имени подкатегории по ID - get_subcategory_name_by_id()

    search_text = (
        "🔎 <b>Поиск по названию</b>\n\n"
        "Введите название вещи, которую хотите найти.\n"
        "Например: 'палатка', 'велосипед', 'дрель'...\n\n"
        "Вы можете искать по любым ключевым словам."
    )
"""