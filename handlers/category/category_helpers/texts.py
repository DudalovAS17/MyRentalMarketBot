from html import escape

from status.item_status import ItemStatus
from schemas.item import ItemOut, ItemCharacteristicOut
from utils.validators import format_price, format_days


not_cat_id = "⚠️ Не удалось распознать категорию."
serv_err_cat = "⚠️ Не удалось загрузить категорию. Попробуйте позже."
not_cat = "⚠️ Категория не найдена"

not_subcat_id = "⚠️ Не удалось распознать подкатегорию."
serv_err_subcat = "⚠️ Не удалось загрузить подкатегорию. Попробуйте позже."
not_subcat = "⚠️ Подкатегория не найдена"

not_item_id = "⚠️ Не удалось распознать товар."
not_item = "⚠️ Товар не найден"
serv_err_item = "⚠️ Не удалось загрузить товар. Попробуйте позже."
serv_err_items = "⚠️ Не удалось загрузить товары. Попробуйте позже."

serv_err_photo = "⚠️ Не удалось загрузить фото. Попробуйте позже."
not_photos = "⚠️ Фото для этого товара не найдены." # 📭 У этого товара нет фотографий

def characteristics_block(characteristics: list[ItemCharacteristicOut], *, limit: int = 5) -> str:
    """Сформировать красивый блок характеристик."""
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
    """Обрезать длинный текст без грубого разрыва."""
    if not value:
        return "Описание пока не добавлено."

    value = value.strip()

    if len(value) <= limit:
        return value

    return value[: limit - 3].rstrip() + "..."

def item_availability_text(item: ItemOut) -> str:
    """Понятный клиентский статус товара для карточки MVP."""
    if item.status != ItemStatus.ACTIVE:
        return "⛔ Сейчас недоступно"
    if item.available_quantity > 0:
        return f"✅ В наличии: <b>{item.available_quantity} шт.</b>"
    return "🟡 Наличие уточняет менеджер"

def item_details_text(
    item: ItemOut,
    category_name: str,
    subcategory_name: str,
    characteristics: list[ItemCharacteristicOut],
) -> str:
    """Сформировать красивую подробную карточку товара."""

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
    """Карточка товара для карусели внутри подкатегории."""

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