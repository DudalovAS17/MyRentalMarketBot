from decimal import Decimal

from schemas.item import ItemOut

not_item_id = "⚠️ Не удалось распознать товар." # ❌ Ошибка: некорректный ID товара.
not_item_for_rental = "❌ Не удалось определить товар для аренды. Начните заново."
not_item = "⚠️ Товар не найдено" # "❌ Товар не найдено. Возможно, оно удалено."

serv_item_err = "⚠️ Не удалось загрузить товар. Попробуйте позже." # serv_err_item
#date_err_msg = "⚠️ Некорректная дата начала аренды. Попробуйте начать аренду заново."
rental_data_err = "❌ Данные аренды повреждены. Начните заново."
not_all_rental_data_err = "❌ Не хватает данных для создания аренды. Начните заново."
no_rent_data_err = "❌ Не удалось восстановить данные аренды. Начните заново."
cancel_rent = "❌ <b>Аренда отменена.</b>\n\nВы можете вернуться к товару или в меню."

item_not_available_message = f"⛔ Этот товар недоступен"

# Текст первого экрана заявки
# Текст экрана подтверждения аренды
# Текст экрана успеха для заявки.

def format_rent_period_text(item: ItemOut) -> str:
    """Текст первого экрана заявки."""
    return (
        f"🤝 <b>Заказ на аренду</b>\n\n"
        f"Вы собираетесь арендовать: <b>{item.title}</b>\n"
        f"💰 Базовая цена: <b>{item.price} ₽/день</b>\n\n"
        "Выберите срок аренды:"
    )

def format_rent_confirmation_text(item: ItemOut, period_text: str, total_price: Decimal) -> str: # total_price: Decimal | None
    """Текст экрана подтверждения аренды."""
    # price_line = (
    #     f"💰 Расчётная стоимость: <b>{total_price} ₽</b>\n\n"
    #     if total_price is not None
    #     else "💰 Итоговую стоимость менеджер уточнит после обработки заявки.\n\n"
    # )

    return (
        f"🤝 <b>Подтверждение аренды</b>\n\n"
        f"📦 Вы собираетесь арендовать товар: <b>{item.title}</b>\n"

        f"<b>Выбранный период:</b>\n"
        #f"📅 Начало: <b>{start_date_str}</b>\n"
        #f"📅 Окончание: <b>{end_date_str}</b>\n"
        f"⏱️ Срок аренды: <b>{period_text}</b>\n\n"

        f"<b>Расчёт стоимости:</b>\n"
        f"💰 Цена: <b>{item.price}</b>\n"
        #f"💰 {price_per_day} ₽/день × {days} дн. = <b>{total_price} ₽</b>\n"
        f"💵 Итого к оплате: <b>{total_price} ₽</b>\n\n"
    )

def build_success_text(item: ItemOut, period_text: str, total_price: Decimal | None) -> str:
    """Текст экрана успеха для заявки."""
    return (
        f"✅ <b>Заявка на аренду отправлена!</b>\n\n"
        f"📦 <b>{item.title}</b>\n"
        f"⏱️ Срок: <b>{period_text}</b>\n"
        f"💰 Стоимость: <b>{total_price} ₽</b>\n" if total_price is not None else ""
        f"ℹ️ Статус: <b>Ожидает обработки менеджером</b>\n\n"
        f"Вы получите уведомление, когда менеджер обработает вашу заявку."
    )