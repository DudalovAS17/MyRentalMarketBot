from html import escape
from typing import Sequence
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from services.item_service import ItemService

from schemas.item import ItemOut
from utils.validators import format_price
from utils.callbacks import (BACK_TO_MENU_CB, PAGE_SIZE, QUERY_MIN_LEN, QUERY_MAX_LEN, SEARCH_PAGE_CB_PREFIX,
                             SEARCH_NEW_QUERY_CB, BACK_TO_CAT) # SEARCH_BACK_CB,

def truncate_text(text: str, max_len: int) -> str:
    """Обрезать текст без разрыва слов и добавить многоточие."""
    normalized = " ".join((text or "").split())
    if len(normalized) <= max_len:
        return normalized

    truncated = normalized[:max_len].rsplit(" ", 1)[0].strip()
    return f"{truncated or normalized[:max_len].strip()}…"

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
        "🔎 <b>Поиск оборудования</b>\n\n"
        "Введите название оборудования или ключевое слово.\n"
        "Например: <i>виброплита</i>, <i>генератор</i>, <i>перфоратор</i>."
    )

def build_empty_search_results_text(query: str) -> str:
    """Сформировать текст пустой выдачи."""
    return (
        f"🔍 <b>Поиск:</b> {escape(query)}\n\n"
        "По вашему запросу ничего не найдено.\n"
        "Попробуйте другое название или откройте каталог."
    )

def build_search_results_text(query: str, items, page: int) -> str:
    """Сформировать текст страницы результатов поиска."""

    if not items:
        return build_empty_search_results_text(query)

    header = (
        f"🔍 <b>Поиск оборудования</b>\n"
        f"Запрос: <i>{escape(query)}</i>\n"
        f"Страница: {page} • Показано: {len(items)} товаров\n\n"
        "Выберите подходящий товар ниже:\n"
    )

    cards = []
    for index, item in enumerate(items, start=1):
        short_description = getattr(item, "short_description", None) or getattr(item, "description", "") or ""
        short_description = truncate_text(short_description, 95)

        card_lines = [
            f"<b>{index}. {escape(item.title)}</b>",
            f"💰 {format_price(item.price)} ₽/сутки",
        ]
        if short_description:
            card_lines.append(f"📝 {escape(short_description)}")

        cards.append("\n".join(card_lines))

    return header + "\n".join(cards)

# ─────────────────────────────────────────────── Keyboard ─────────────────────────────────────────────────────────────
def build_search_prompt_keyboard() -> InlineKeyboardMarkup:
    """Собрать клавиатуру prompt-экрана поиска."""
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🏠 Главное меню", callback_data=BACK_TO_MENU_CB)]]
    )

def build_search_keyboard(items: Sequence[ItemOut], page: int, has_next: bool) -> InlineKeyboardMarkup:
    """Собрать клавиатуру карточной поисковой выдачи."""
    keyboard: list[list[InlineKeyboardButton]] = []

    for item in items:
        keyboard.append([InlineKeyboardButton(
            text=f"🔎 Открыть товар #{item.id}",
            callback_data=f"show_item_details:{item.id}")]
        )

    has_prev = page > 1
    nav_row: list[InlineKeyboardButton] = []
    if has_prev:
        nav_row.append(InlineKeyboardButton(text="⬅️", callback_data=f"{SEARCH_PAGE_CB_PREFIX}{page - 1}"))
    if items:
        nav_row.append(InlineKeyboardButton(text=f"Стр. {page}", callback_data="noop"))
    if has_next:
        nav_row.append(InlineKeyboardButton(text="➡️", callback_data=f"{SEARCH_PAGE_CB_PREFIX}{page + 1}"))
    if nav_row:
        keyboard.append(nav_row)

    keyboard.append([InlineKeyboardButton(text="🔎 Новый поиск", callback_data=SEARCH_NEW_QUERY_CB)])
    if not items:
        keyboard.insert(0, [InlineKeyboardButton(text="🏗 Открыть каталог", callback_data=BACK_TO_CAT)])
    keyboard.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data=BACK_TO_MENU_CB)])
    # "🔙 Назад" - callback_data="search:back"

    return InlineKeyboardMarkup(inline_keyboard=keyboard)

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