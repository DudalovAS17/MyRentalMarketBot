import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram.fsm.context import FSMContext

from services.item_service import ItemService
from states.search import SearchStates
from keyboards.search_kb import build_search_keyboard
from utils.functions import format_price, send_or_edit


PAGE_SIZE = 8
QUERY_MIN_LEN = 2
QUERY_MAX_LEN = 60


def normalize_search_query(raw: str | None) -> str:
    """Нормализовать поисковый запрос."""
    return (raw or "").strip()

def validate_search_query(query: str) -> str | None:
    """Проверить поисковый запрос."""
    if not (QUERY_MIN_LEN <= len(query) <= QUERY_MAX_LEN):
        return "Запрос должен быть длиной от 2 до 60 символов. Попробуйте ещё раз."

    return None


# ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
def render_results_text(query: str, items, page: int) -> str:
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

async def prompt_search_query(event: Message | CallbackQuery, state: FSMContext) -> None:
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

async def fetch_search_page(query: str, page: int, item_service: ItemService):
    safe_page = max(page, 1)
    offset = (safe_page - 1) * PAGE_SIZE
    items = await item_service.search_items(query, available_only=True, limit=PAGE_SIZE + 1, offset=offset)
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


async def show_search_results(
    event: Message | CallbackQuery,
    state: FSMContext,
    item_service: ItemService,
    page: int | None = None,
):
    data = await state.get_data()
    query = data.get("search_query")
    if not query:
        return await prompt_search_query(event, state)

    current_page = page or data.get("search_page", 1)
    items, has_next, safe_page = await fetch_search_page(query, current_page, item_service)
    await state.update_data(search_page=safe_page)

    text = render_results_text(query, items, safe_page)
    keyboard = build_search_keyboard(items, safe_page, has_next)
    return await send_or_edit(event, text, markup=keyboard)