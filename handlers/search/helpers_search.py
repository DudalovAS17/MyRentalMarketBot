from html import escape
from typing import Sequence
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from services.item_service import ItemService

from schemas.item import ItemOut
from utils.functions import format_price
from utils.callbacks import ITEM_DETAILS_CB, BACK_TO_MENU_CB

PAGE_SIZE = 8
QUERY_MIN_LEN = 2
QUERY_MAX_LEN = 60
SEARCH_PAGE_CB_PREFIX = "search:page:"
SEARCH_NEW_QUERY_CB = "search:new_query"
SEARCH_BACK_CB = "search:back"

# ─────────────────────────────────────── Parse and Validate ───────────────────────────────────────────────────────────
def normalize_search_query(raw: str | None) -> str:
    """Нормализовать поисковый запрос."""
    return " ".join((raw or "").strip().split())

def validate_search_query(query: str) -> str | None:
    """Проверить поисковый запрос."""
    if not (QUERY_MIN_LEN <= len(query) <= QUERY_MAX_LEN):
        return "Запрос должен быть длиной от 2 до 60 символов. Попробуйте ещё раз."

    return None

def parse_search_page(raw: str | None) -> int | None:
    """Распарсить номер страницы поиска"""
    if not raw or not raw.startswith(SEARCH_PAGE_CB_PREFIX):
        return None

    try:
        page = int(raw.removeprefix(SEARCH_PAGE_CB_PREFIX))
        #page = int((raw or "").split(":")[-1])
    except ValueError:
        return None

    return max(1, page)

# ─────────────────────────────────────────── Text ─────────────────────────────────────────────────────────────────────
def build_search_prompt_text() -> str:
    """Сформировать prompt ввода поискового запроса."""
    return (
        "🔎 <b>Поиск по каталогу</b>\n\n"
        "Введите название вещи или ключевое слово.\n"
        "Например: <i>сварка</i>, <i>болгарка</i>, <i>дрель</i>."
    )

def build_empty_search_results_text(query: str) -> str:
    """Сформировать текст пустой выдачи."""
    return (
        f"🔍 <b>Поиск:</b> {escape(query)}\n\n"
        "📭 Ничего не найдено. Попробуйте изменить запрос."
    )

def build_search_results_text(query: str, items, page: int) -> str:
    """Сформировать текст страницы результатов поиска."""

    header = f"🔍 <b>Поиск:</b> {escape(query)}\n Страница: {page}\n\n"
    if not items:
        return f"{header} 📭 Ничего не найдено. Попробуйте изменить запрос."

    lines = []
    for item in items:
        lines.append(f"• {escape(item.title)} — {format_price(item.price)} ₽")

    return header + "\n".join(lines)

# ─────────────────────────────────────────────── Keyboard ─────────────────────────────────────────────────────────────
def build_search_prompt_keyboard() -> InlineKeyboardMarkup:
    """Собрать клавиатуру prompt-экрана поиска."""
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data=SEARCH_BACK_CB )]] # back_to_main_menu
    )

def build_search_results_keyboard(items: Sequence[ItemOut], page: int, has_next: bool) -> InlineKeyboardMarkup:
    """Собрать клавиатуру карточной поисковой выдачи."""
    buttons: list[list[InlineKeyboardButton]] = []

    if items:
        buttons.append([InlineKeyboardButton(text="🔍 Подробнее", callback_data=f"{ITEM_DETAILS_CB}{items[0].id}")])

    nav_row: list[InlineKeyboardButton] = []
    if page > 1:
        nav_row.append(InlineKeyboardButton(text="⬅️", callback_data=f"{SEARCH_PAGE_CB_PREFIX}{page - 1}"))
    if items:
        nav_row.append(InlineKeyboardButton(text=f"Стр. {page}", callback_data="noop"))
    if has_next:
        nav_row.append(InlineKeyboardButton(text="➡️", callback_data=f"{SEARCH_PAGE_CB_PREFIX}{page + 1}"))
    if nav_row:
        buttons.append(nav_row)

    buttons.append([InlineKeyboardButton(text="✏️ Новый запрос", callback_data=SEARCH_NEW_QUERY_CB)])
    buttons.append([InlineKeyboardButton(text="🔙 Назад в меню", callback_data=BACK_TO_MENU_CB)])

    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ──────────────────────────────────────── Страницу результатов поиска ─────────────────────────────────────────────────
async def fetch_search_page(query: str, page: int, item_service: ItemService):
    """Загрузить страницу результатов поиска."""
    safe_page = max(page, 1)
    items = await item_service.search_items(
        query,
        available_only=True,
        limit=PAGE_SIZE + 1,
        offset=(safe_page - 1) * PAGE_SIZE
    )

    has_next = len(items) > PAGE_SIZE
    return items[:PAGE_SIZE], has_next, safe_page