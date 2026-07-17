"""Генераторы HTML для Telegram Rich Message API.

Rich-сообщения отправляются через ``InputRichMessage`` и методы aiogram
``answer_rich``/``reply_rich``/``send_rich_message``. Это не замена
обычному ``parse_mode='HTML'``: теги ``table``, ``tg-slideshow``,
``tg-collage``, ``details`` и другие rich-блоки не предназначены для
``message.answer(..., parse_mode='HTML')``.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from html import escape
from typing import Any

from aiogram.types import InputRichMessage


TariffRow = Mapping[str, Any]
TableRow = Sequence[Any]


def html_escape(value: Any) -> str:
    """Экранирует пользовательские данные перед вставкой в rich HTML."""
    return escape("" if value is None else str(value), quote=True)


def build_rich_message(html: str, *, skip_entity_detection: bool = True) -> InputRichMessage:
    """Создаёт aiogram ``InputRichMessage`` из HTML-разметки."""
    return InputRichMessage(html=html, skip_entity_detection=skip_entity_detection)


def build_table_html(headers: Sequence[Any], rows: Iterable[TableRow], *, bordered: bool = True, striped: bool = True) -> str:
    """Собирает rich-таблицу с экранированием значений ячеек.

    ``headers`` рендерятся жирным, ``rows`` — обычными ячейками. Флаги
    ``bordered`` и ``striped`` добавляют одноимённые атрибуты Telegram rich HTML.
    """
    attrs = "".join((" bordered" if bordered else "", " striped" if striped else ""))
    header_html = "".join(f"<td><strong>{html_escape(header)}</strong></td>" for header in headers)
    body_html = "\n".join(
        "  <tr>" + "".join(f"<td>{html_escape(cell)}</td>" for cell in row) + "</tr>"
        for row in rows
    )

    return f"<table{attrs}>\n  <tr>{header_html}</tr>\n{body_html}\n</table>"


def build_tariffs_table_html(tariffs: Iterable[TariffRow] | None = None) -> str:
    """Генерирует таблицу тарифов для rich-сообщения."""
    default_tariffs: tuple[TariffRow, ...] = (
        {"name": "Start", "price": "299₽", "limit": "100 запросов"},
        {"name": "Pro", "price": "799₽", "limit": "500 запросов"},
    )
    source = tuple(tariffs or default_tariffs)
    rows = ((tariff.get("name", ""), tariff.get("price", ""), tariff.get("limit", "")) for tariff in source)
    return build_table_html(("Тариф", "Цена", "Лимит"), rows)


def build_images_slideshow_html(images: Sequence[str]) -> str:
    """Генерирует ``tg-slideshow`` для карусели изображений."""
    image_tags = "\n".join(f'  <img src="{html_escape(src)}">' for src in images if src)
    return f"<tg-slideshow>\n{image_tags}\n</tg-slideshow>"


def build_images_collage_html(images: Sequence[str]) -> str:
    """Генерирует ``tg-collage`` для показа нескольких изображений одним блоком."""
    image_tags = "\n".join(f'  <img src="{html_escape(src)}">' for src in images if src)
    return f"<tg-collage>\n{image_tags}\n</tg-collage>"


def build_user_stats_html(user: Mapping[str, Any]) -> str:
    """Генерирует compact rich-блок со статистикой пользователя."""
    rows = (
        ("Имя", user.get("name") or user.get("full_name") or "—"),
        ("Город", user.get("city") or "—"),
        ("Аренды", user.get("rentals_count", 0)),
        ("Рейтинг", user.get("rating", "—")),
    )
    return "\n".join((
        "<h2>Профиль</h2>",
        "<p>Краткая статистика пользователя.</p>",
        build_table_html(("Показатель", "Значение"), rows),
    ))


def build_details_html(summary: Any, body_html: str) -> str:
    """Оборачивает длинное описание в раскрывающийся rich-блок ``details``."""
    return f"<details>\n  <summary>{html_escape(summary)}</summary>\n  {body_html}\n</details>"