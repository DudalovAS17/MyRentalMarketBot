from html import escape

from status.item_status import ItemStatus
from schemas.item import ItemOut, ItemCharacteristicOut
from utils.validators import format_price #, format_days
from texts_otP.error_empty_states import ITEM_NOT_FOUND

not_item = ITEM_NOT_FOUND

not_cat_id = "⚠️ Не удалось распознать категорию."
serv_err_cat = "⚠️ Не удалось загрузить категорию. Попробуйте позже."
not_cat = "⚠️ Категория не найдена"

not_subcat_id = "⚠️ Не удалось распознать подкатегорию."
serv_err_subcat = "⚠️ Не удалось загрузить подкатегорию. Попробуйте позже."
not_subcat = "⚠️ Подкатегория не найдена"

not_item_id = "⚠️ Не удалось распознать товар."
serv_err_item = "⚠️ Не удалось загрузить товар. Попробуйте позже."
serv_err_items = "⚠️ Не удалось загрузить товары. Попробуйте позже."

serv_err_photo = "⚠️ Не удалось загрузить фото. Попробуйте позже."
not_photos = "⚠️ Фото для этого товара не найдены." # 📭 У этого товара нет фотографий

delivery = ("Доставка осуществляется по городу от 200 руб в зависимости от района. \n"
            "Доставка тяжелой техники осуществляется от 800 руб. \n"
            "Подробнее уточняйте у менеджера \n\n")

all_prices = [
    ("1 день", "1400 RUB"),
    ("2-7 дня", "1300 RUB/день"),
    ("8-14 дней", "1200 RUB/день"),
    ("> 15 дней", "1100 RUB/день"),
]

min_price = "Аренда от 1100 RUB"

def item_details_text(
    item: ItemOut,
    category_name: str,
    subcategory_name: str,
    characteristics: list[ItemCharacteristicOut],
) -> str:
    """Сформировать rich-карточку товара с мини-таблицами."""

    #description = escape(trim_text(item.description or item.short_description, limit=300))
    description = escape(item.description or item.short_description)
    title = escape(item.title)
    category_path = f"{escape(category_name)} → {escape(subcategory_name)}"

    return (
        f"<h2>📦 {title}</h2>\n"
        f"{item_prices_table()}\n" # item_summary_table(item)

        #f"<p><strong>🏷️ Раздел</strong><br>{category_path}</p>\n"
        
        f"<details>"
        f"<summary>📝 Описание</summary>"
        f"<p>{description}</p>"
        f"</details>\n"

        f"<details>"
        f"<summary>⚙️ Характеристики</summary>"
        f"{characteristics_table(characteristics, limit=7)}\n"
        f"</details>\n"
        
        f"<details>"
        f"<summary>📝 Доставка </summary>"
        f"<p>{delivery}</p>"
        f"</details>\n"

        #f"⭐ <b>Рейтинг:</b> ... ({item.views_count} отзывов)\n"

        #f"<p>👇 Выберите действие ниже</p>"
    )


# availability_text = "Доступно для аренды" if item.is_available else "Временно недоступно"

# карусель
def subcategory_item_card_text(
    item: ItemOut,
    current_index: int,
    total_items: int,
    characteristics: list[ItemCharacteristicOut],
) -> str:
    """Rich-карточка товара для карусели внутри подкатегории."""
    return (
        f"<h2>{escape(item.title)}</h2>\n" # 📦 
        f"<p><strong>💰{min_price} | {item_availability_text(item)} </strong></p>\n"
        #f"<p>📍 <strong>{current_index + 1} из {total_items}</strong></p>"
    )

# ──────────────────────────────────────────── helpers for helper ──────────────────────────────────────────────────────
def rich_table(rows: list[tuple[str, str]]) -> str:
    """Сформировать компактную rich-таблицу из двух колонок."""
    table_rows = [
        "  <tr>"
        f"<td>{escape(label)}</td>"
        f"<td><strong>{escape(value)}</strong></td>"
        "</tr>"
        for label, value in rows
    ]
    return "<table bordered striped>\n" + "\n".join(table_rows) + "\n</table>"

def item_summary_table(item: ItemOut) -> str:
    """Сформировать rich-таблицу с ценой, сроком и наличием."""
    availability = item_availability_text(item)
    return rich_table(
        [
            ("💰 Цена", f"{format_price(item.price)} ₽ / день"),
            ("✅ Наличие:", availability),
        ]
    )

def item_prices_table() -> str:
    """Сформировать rich-таблицу с ценой товара"""
    return rich_table(all_prices)

def characteristics_table(characteristics: list[ItemCharacteristicOut], *, limit: int = 5) -> str:
    """Сформировать rich-таблицу характеристик."""
    visible_characteristics = list(characteristics[:limit])
    if not visible_characteristics:
        return "<p>⚙️ Характеристики пока не добавлены</p>"

    rows = [(characteristic.name, characteristic.value) for characteristic in visible_characteristics]
    return rich_table(rows)

def item_availability_text(item: ItemOut) -> str:
    """Понятный клиентский статус товара для карточки MVP."""
    if item.status != ItemStatus.ACTIVE:
        return "⛔ Сейчас недоступно"
    if item.available_quantity > 0:
        return f"✅ В наличии: <b>{item.available_quantity} шт.</b>"
    return "🟡 Наличие уточняет менеджер"


# Карточки товаров без rich-логики
"""
def characteristics_block(characteristics: list[ItemCharacteristicOut], *, limit: int = 5) -> str:
    ""Сформировать красивый блок характеристик.""
    if not characteristics:
        return "• Характеристики пока не добавлены"

    visible_characteristics = list(characteristics[:limit])
    lines: list[str] = []

    for index, characteristic in enumerate(visible_characteristics):
        if index == 0 and len(visible_characteristics) == 1:
            prefix = "└"
        elif index == 0:
            prefix = "┌"
        elif index == len(visible_characteristics) - 1:
            prefix = "└"
        else:
            prefix = "├"

        lines.append(
            f"{prefix} <b>{characteristic.name}:</b> {characteristic.value}"
        )

    return "\n".join(lines)

def trim_text(value: str | None, limit: int = 260) -> str:
    ""Обрезать длинный текст без грубого разрыва.""
    if not value:
        return "Описание пока не добавлено."

    value = value.strip()

    if len(value) <= limit:
        return value

    return value[: limit - 3].rstrip() + "..."

def item_details_text(
    item: ItemOut,
    category_name: str,
    subcategory_name: str,
    characteristics: list[ItemCharacteristicOut],
) -> str:
    ""Сформировать красивую подробную карточку товара.""

    min_period = format_days(item.min_rental_period)
    description = trim_text(item.description or item.short_description, limit=300)

    return (
        f"📦 <b>{item.title}</b>\n\n"
        f"💰 <b>{format_price(item.price)} ₽ / день</b>\n"
        f"{item_availability_text(item)}\n"
        f"📅 Минимальный срок аренды: <b>{min_period}</b>\n\n"
        f"⚙️ <b>Характеристики</b>\n"
        f"{characteristics_block(characteristics, limit=7)}\n\n"
        f"🏷️ <b>Раздел</b>\n"
        f"{category_name} → {subcategory_name}\n\n"
        f"📝 <b>Описание</b>\n"
        f"{description}\n\n"
        f"👇 Выберите действие ниже"
    )
#f"⭐ <b>Рейтинг:</b> ... ({item.views_count} отзывов)\n"
# availability_text = "Доступно для аренды" if item.is_available else "Временно недоступно"

# карусель
def subcategory_item_card_text(
    item: ItemOut,
    current_index: int,
    total_items: int,
    characteristics: list[ItemCharacteristicOut],
) -> str:
    ""Карточка товара для карусели внутри подкатегории.""

    min_period = item.min_rental_period or 1
    characteristics_text = "\n".join(
        f"• <b>{escape(characteristic.name)}:</b> {escape(characteristic.value)}"
        for characteristic in characteristics
    )
    if not characteristics_text:
        characteristics_text = "• Характеристики пока не добавлены"

    return (
        f"📦 <b>{escape(item.title)}</b>\n\n"
        f"💰 <b>{format_price(item.price)} ₽ / день</b>\n"
        f"📅 Мин. срок: <b>{min_period} {format_days(min_period)}</b>\n"
        f"{item_availability_text(item)}\n\n"
        f"⚙️ <b>Характеристики:</b>\n"
        f"{characteristics_text}\n\n"
        f"📍 <b>{current_index + 1} из {total_items}</b>"

        # f"👁 Просмотры: {item.views_count}\n\n"
    )
"""
