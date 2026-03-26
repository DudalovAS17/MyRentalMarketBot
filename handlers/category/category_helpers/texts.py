from utils.functions import format_price, format_days

not_cat_id = "⚠️ Не удалось распознать категорию."
serv_err_cat = "⚠️ Не удалось загрузить категорию. Попробуйте позже."
not_cat = "⚠️ Категория не найдена"

not_subcat_id = "⚠️ Не удалось распознать подкатегорию."
serv_err_subcat = "⚠️ Не удалось загрузить подкатегорию. Попробуйте позже."
not_subcat = "⚠️ Подкатегория не найдена"

not_item_id = "⚠️ Не удалось распознать объявление."
not_item = "⚠️ Объявление не найдено"
serv_err_item = "⚠️ Не удалось загрузить объявление. Попробуйте позже."
serv_err_items = "⚠️ Не удалось загрузить объявления. Попробуйте позже." # тут путаница?

serv_err_photo = "⚠️ Не удалось загрузить фото. Попробуйте позже."
not_photos = "⚠️ Фото для этого объявления не найдены." # 📭 У этого объявления нет фотографий

def item_details_text(item, category_name: str, subcategory_name: str) -> str: # item: Any
    description = item.description or "Описание не указано"
    location = item.location or "Не указано"
    min_rental_period = item.min_rental_period or 1
    deposit_text = f"{format_price(item.deposit)} ₽" if item.deposit else "Без залога"
    availability_text = "Доступно для аренды" if item.is_available else "Временно недоступно"

    return (
        f"📦 <b>{item.title}</b>\n\n"
        f"📝 <b>Описание:</b>\n{description}\n\n"
        f"🏷️ <b>Категория:</b> {category_name} > {subcategory_name}\n"
        f"💰 <b>Цена:</b> {format_price(item.price)} ₽/день\n"
        f"🕒 <b>Минимальный срок аренды:</b> {min_rental_period} {format_days(min_rental_period)}\n"
        f"🔐 <b>Залог:</b> {deposit_text}\n"
        f"📍 <b>Местоположение:</b> {location}\n"
        #f"👤 <b>Владелец:</b> {item.user_id}\n"
        #f"⭐ <b>Рейтинг:</b> ... ({item.views_count} отзывов)\n"
        f"✅ <b>Доступность:</b> {availability_text}\n\n"
    )