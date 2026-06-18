from schemas.item import ItemOut
from utils.functions import format_price, format_days

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

def item_details_text(item: ItemOut, category_name: str, subcategory_name: str) -> str:
    """Сформировать текст карточки товара для карусели подкатегории."""

    description = item.short_description or item.description or "Описание пока не добавлено."
    if len(description) > 180:
        description = description[:177].rstrip() + "..."

    return (
        f"📦 <b>{item.title}</b>\n\n"
        f"📝 <b>Описание:</b>\n{description}\n\n"
        f"🏷️ <b>Категория:</b> {category_name} > {subcategory_name}\n"
        f"💰 <b>Цена:</b> {format_price(item.price)} ₽/день\n"
        f"🕒 <b>Минимальный срок аренды:</b> {item.min_rental_period} \n" # {format_days(min_rental_period)}
        # f"🔐 <b>Залог:</b> {deposit_text}\n"
        # f"📍 <b>Местоположение:</b> {location}\n"
        #f"👤 <b>Владелец:</b> {item.user_id}\n"
        #f"⭐ <b>Рейтинг:</b> ... ({item.views_count} отзывов)\n"
        f"✅ <b>Доступное количество:</b> {item.available_quantity}\n"
    )
# location = item.location or "Не указано"
# deposit_text = f"{format_price(item.deposit)} ₽" if item.deposit else "Без залога"
# availability_text = "Доступно для аренды" if item.is_available else "Временно недоступно"

# карусель
def subcategory_item_card_text(item: ItemOut, current_index: int, total_items: int) -> str:
    """Карточка товара для карусели внутри подкатегории."""

    short_description = item.short_description or item.description or "Описание не указано"
    min_period = item.min_rental_period or 1

    return (
        f"📦 <b>{item.title}</b>\n\n"
        f"📝 {short_description}\n"
        f"💰 Цена: <b>{format_price(item.price)} ₽/день</b>\n"
        #f"📍 Локация: {location}\n"
        f"🗓 Мин. срок: {min_period} {format_days(min_period)}\n"
        f"✅ Количество: {item.available_quantity}\n"
        f"👁 Просмотры: {item.views_count}\n\n"
        f"{current_index + 1} / {total_items}"
    )
# location = item.location or "Не указана"