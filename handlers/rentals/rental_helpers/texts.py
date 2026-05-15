from decimal import Decimal

from schemas.item import ItemOut
from utils.domain_exceptions import ItemNotAvailable


not_item_id = "⚠️ Не удалось распознать объявление." # ❌ Ошибка: некорректный ID объявления.
not_item_for_rental = "❌ Не удалось определить объявление для аренды. Начните заново."
not_item = "⚠️ Объявление не найдено" # "❌ Объявление не найдено. Возможно, оно удалено."
serv_item_err = "⚠️ Не удалось загрузить объявление. Попробуйте позже." # serv_err_item
date_err_msg = "⚠️ Некорректная дата начала аренды. Попробуйте начать аренду заново."
rental_data_err = "❌ Данные аренды повреждены. Начните заново."
not_all_rental_data_err = "❌ Не хватает данных для создания аренды. Начните заново."
no_rent_data_err = "❌ Не удалось восстановить данные аренды. Начните заново."
cancel_rent = "❌ <b>Аренда отменена.</b>\n\nВы можете вернуться к объявлению или в меню."


def format_item_not_available_message(exc: ItemNotAvailable) -> str:
    """Сформировать UX-текст для случая, когда вещь уже недоступна для аренды"""
    end_str = exc.end_date if exc.end_date else ""
    status = exc.status or "—"
    rental_id = exc.rental_id or "—"
    if end_str:
        return f"⛔ Эта вещь уже в аренде до {end_str}. Сделка #{rental_id} статус {status}."
    return f"⛔ Эта вещь уже в аренде. Сделка #{rental_id} статус {status}."


def format_start_date_rent_text(item: ItemOut) -> str:
    """Формирует текст первого экрана аренды"""
    return (
        f"🤝 <b>Аренда вещи</b>\n\n"
        f"Вы собираетесь арендовать: <b>{item.title}</b>\n"
        f"💰 Цена: <b>{item.price} ₽/день</b>\n"
        f"🔒 Залог: <b>{item.deposit or 'Нет'} ₽</b>\n\n"
        "Выберите дату начала аренды:"
    )


def format_end_date_rent_text(item: ItemOut, start_str: str) -> str:
    """Формирует текст шага-выбора даты окончания"""
    return (
        f"🤝 <b>Аренда вещи</b>\n\n"
        f"Вы собираетесь арендовать товар: <b>{item.title}</b>\n"
        f"📅 Дата начала аренды: <b>{start_str}</b>\n"
        f"💰 Цена: <b>{item.price} ₽/день</b>\n"
        f"🔒 Залог: <b>{item.deposit or 'Нет'} ₽</b>\n\n"
        "Теперь выберите дату окончания аренды:"
    )


def format_rent_confirmation_text(
        item: ItemOut,
        start_date_str: str,
        end_date_str: str,
        days: int,
        price_per_day: Decimal,
        total_price: Decimal,
        deposit: Decimal,
        total_with_deposit: Decimal,
) -> str:
    """Текст экрана подтверждения аренды"""

    return (
        f"🤝 <b>Подтверждение аренды</b>\n\n"
        f"📦 <b>{item.title}</b>\n"
        # f"👤 Владелец: {...}\n"
        f"📍 {item.location or '-'}\n\n"

        f"<b>Выбранный период:</b>\n"
        f"📅 Начало: <b>{start_date_str}</b>\n"
        f"📅 Окончание: <b>{end_date_str}</b>\n"
        f"⏱️ Длительность: <b>{days} дн.</b>\n\n"

        f"<b>Расчёт стоимости:</b>\n"
        f"💰 {price_per_day} ₽/день × {days} дн. = <b>{total_price} ₽</b>\n"
        f"🛡 Залог: <b>{deposit if deposit > 0 else 'Нет'} ₽</b>\n"
        f"💵 Итого к оплате (после подтверждения владельцем): <b>{total_with_deposit} ₽</b>\n\n"

        "❗ Залог будет возвращен после завершения аренды и возврата вещи в исходном состоянии.\n\n"
        "Отправить запрос на аренду владельцу?"
    )


def build_success_text(
        item: ItemOut,
        start_date: str,
        end_date: str,
        days: int,
        total_price: Decimal,
        deposit: Decimal,
) -> str:
    """Текст экрана успеха для аренды"""
    return (
        f"✅ <b>Запрос на аренду отправлен!</b>\n\n"
        f"📦 <b>{item.title}</b>\n"
        f"📅 {start_date} — {end_date}\n"
        f"⏱️ {days} дн.\n\n"
        f"💰 Стоимость: <b>{total_price} ₽</b>\n"
        f"💵🛡 Залог: <b>{deposit if deposit is not None else 'Нет'} ₽</b>\n\n"
        f"ℹ️ Статус: <b>Ожидает подтверждения владельцем</b>\n\n"
        f"Вы получите уведомление, когда владелец ответит на ваш запрос."
    )
