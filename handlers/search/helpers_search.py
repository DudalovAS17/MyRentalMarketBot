from html import escape
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from services.item_service import ItemService
from utils.functions import format_price

PAGE_SIZE = 8
QUERY_MIN_LEN = 2
QUERY_MAX_LEN = 60

# ─────────────────────────────────────── Parse and Validate ───────────────────────────────────────────────────────────
def normalize_search_query(raw: str | None) -> str:
    """Нормализовать поисковый запрос."""
    return (raw or "").strip()

def validate_search_query(query: str) -> str | None:
    """Проверить поисковый запрос."""
    if not (QUERY_MIN_LEN <= len(query) <= QUERY_MAX_LEN):
        return "Запрос должен быть длиной от 2 до 60 символов. Попробуйте ещё раз."

    return None

def parse_search_page(raw: str | None) -> int | None:
    """Распарсить номер страницы поиска из callback data."""
    try:
        page = int((raw or "").split(":")[-1])
    except (ValueError, IndexError):
        return None

    return max(1, page)

# ─────────────────────────────────────────── Text ─────────────────────────────────────────────────────────────────────
def build_search_prompt_text() -> str:
    """Сформировать prompt ввода поискового запроса."""
    return "🔎 Введите текст запроса (2–60 символов)."

def build_search_results_text(query: str, items, page: int) -> str:
    """Сформировать текст результатов поиска."""
    safe_query = escape(query)

    header = (
        f"🔍 <b>Поиск:</b> {safe_query}\n"
        f"Страница: {page}\n\n"
    )

    if not items:
        return f"{header}Ничего не найдено. Попробуйте изменить запрос."

    lines = []
    for item in items:
        price = format_price(item.price)
        title = item.title or "Без названия" # escape(item.title or "Без названия")
        location = f" ({item.location})" if item.location else "" # f" ({escape(item.location)})" if item.location else ""
        # code = f"Запрос: <code>{query}</code>\n\n" - можно добавить
        lines.append(f"• {title} — {price} ₽/день{location}")

    return header + "\n".join(lines)

# ─────────────────────────────────────────────── Keyboard ─────────────────────────────────────────────────────────────
def build_search_prompt_keyboard() -> InlineKeyboardMarkup:
    """Собрать клавиатуру prompt-экрана поиска."""
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="search:back", )]] # back_to_main_menu
    )

# ──────────────────────────────────────── Страницу результатов поиска ─────────────────────────────────────────────────
async def fetch_search_page(query: str, page: int, item_service: ItemService):
    """Загрузить страницу результатов поиска."""

    safe_page = max(page, 1)
    offset = (safe_page - 1) * PAGE_SIZE

    items = await item_service.search_items(
        query,
        available_only=True,
        limit=PAGE_SIZE + 1,
        offset=offset,
    )

    has_next = len(items) > PAGE_SIZE
    return items[:PAGE_SIZE], has_next, safe_page