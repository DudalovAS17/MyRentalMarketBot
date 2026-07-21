from html import escape

from schemas.item import ItemOut
from schemas.rental import RentalCreateDraft

not_item_id = "⚠️ Не удалось распознать товар." # ❌ Ошибка: некорректный ID товара.
not_item_for_rental = "❌ Не удалось определить товар для аренды. Начните заново."
not_item = "⚠️ Товар не найдено" # "❌ Товар не найдено. Возможно, оно удалено."

serv_item_err = "⚠️ Не удалось загрузить товар. Попробуйте позже." # serv_err_item
#date_err_msg = "⚠️ Некорректная дата начала аренды. Попробуйте начать аренду заново."
rental_data_err = "❌ Данные аренды повреждены. Начните заново."
not_all_rental_data_err = "❌ Не хватает данных для создания аренды. Начните заново."
no_rent_data_err = "❌ Не удалось восстановить данные аренды. Начните заново."
cancel_rent = "❌ <b>Заявка отменена.</b>\n\nВы можете вернуться к товару или в меню."

item_not_available_message = f"⛔ Этот товар недоступен"

RENTAL_DETAILS_LOAD_ERROR = "⚠️ Не удалось загрузить детали заявки. Попробуйте позже."
RENTAL_DETAILS_ACCESS_ERROR = "❌ Заявка не найдена или у вас нет доступа."
INVALID_RENTAL_ID_TEXT = "Некорректный id заявки."


def _safe(value: object | None, default: str = "—") -> str:
    """Безопасно подготовить значение."""
    if value is None:
        return default
    text = str(value).strip()
    return escape(text) if text else default

def _delivery_line(draft: RentalCreateDraft) -> str:
    """Вернуть человекочитаемое состояние доставки из draft заявки."""
    if draft.delivery_needed: #  is True
        return "нужна"
    if draft.delivery_needed is False:
        return "не нужна"
    return "—"

# ───────────────────────────────────────── for Rental FSM ─────────────────────────────────────────────────────────────
def format_rent_quantity_text(item: ItemOut) -> str:
    """Сформировать текст шага выбора количества."""
    return (
        "🤝 <b>Заявка на аренду</b>\n\n"
        f"Товар: <b>{_safe(item.title)}</b>\n"
        f"Доступно: <b>{item.available_quantity}</b>\n\n"
        "Укажите количество: выберите кнопку или отправьте число сообщением."
    )

def format_rent_period_text(item: ItemOut) -> str:
    """Сформировать текст шага выбора срока аренды."""
    return (
        f"🤝 <b>Заявка на аренду</b>\n\n"
        f"Вы собираетесь арендовать: <b>{_safe(item.title)}</b>\n"
        f"💰 Базовая цена: <b>{item.price} ₽/день</b>\n\n"
        "Выберите ориентировочный срок аренды. Точные дни менеджер уточнит по звонку."
    )

def format_rent_delivery_text(item: ItemOut, draft: RentalCreateDraft) -> str:
    """Сформировать текст шага выбора доставки."""
    return (
        "🚚 <b>Доставка</b>\n\n"
        f"Товар: <b>{_safe(item.title)}</b>\n"
        f"Количество: <b>{draft.quantity or 1}</b>\n"
        f"Ориентировочный срок: <b>{_safe(draft.rental_period_text)}</b>\n\n"
        "Нужна ли доставка?"
    )

def format_rent_delivery_address_text() -> str:
    """Сформировать текст шага ввода адреса доставки."""
    return "📍 <b>Адрес доставки</b>\n\nУкажите адрес доставки одним сообщением."

def format_rent_client_name_text(profile_name: str | None) -> str:
    """Сформировать текст шага подтверждения или ввода имени клиента."""
    default = f"\n\nИмя из профиля: <b>{_safe(profile_name)}</b>" if profile_name else ""
    return f"👤 <b>Имя клиента</b>{default}\n\nВведите имя или используйте значение из профиля."

def format_rent_client_phone_text(profile_phone: str | None) -> str:
    """Сформировать текст шага подтверждения или ввода телефона клиента."""
    default = f"\n\nТелефон из профиля: <b>{_safe(profile_phone)}</b>" if profile_phone else ""
    return f"☎️ <b>Телефон клиента</b>{default}\n\nВведите телефон или используйте значение из профиля."

def format_rent_comment_text() -> str:
    """Сформировать текст шага комментария клиента."""
    return "💬 <b>Комментарий</b>\n\nНапишите комментарий к заявке или нажмите «Без комментария»."

def format_rent_confirmation_text(item: ItemOut, draft: RentalCreateDraft) -> str:
    """Текст подтверждения заявки."""
    #price_line = f"💵 Расчётная стоимость: <b>{draft.total_price} ₽</b>\n" if draft.total_price is not None else "💵 Расчётная стоимость: менеджер уточнит после обработки\n"
    address_line = f"Адрес: <b>{_safe(draft.delivery_address)}</b>\n" if draft.delivery_needed else ""
    return (
        "✅ <b>Проверьте заявку</b>\n\n"
        f"📦 Товар: <b>{_safe(item.title)}</b>\n"
        f"Количество: <b>{draft.quantity or 1}</b>\n"
        f"Ориентировочный срок: <b>{_safe(draft.rental_period_text)}</b>\n"
        "💵 Предварительно: <b>менеджер рассчитает после уточнения дней</b>\n"
        "🚚 Доставка: <b>менеджер рассчитает по адресу</b>\n"
        f"Доставка нужна: <b>{_delivery_line(draft)}</b>\n"
        f"{address_line}"
        f"Имя: <b>{_safe(draft.client_name)}</b>\n"
        f"Телефон: <b>{_safe(draft.client_phone)}</b>\n"
        f"Комментарий: <b>{_safe(draft.client_comment)}</b>\n\n"
        #f"{price_line}\n"
        "Если всё верно — отправьте заявку менеджеру."

        # f"<b>Выбранный период:</b>\n"
        # f"📅 Начало: <b>{start_date_str}</b>\n"
        # f"📅 Окончание: <b>{end_date_str}</b>\n"
    )

def build_success_text(item: ItemOut, draft: RentalCreateDraft) -> str:
    """Текст успеха после отправки заявки."""
    #price_line = f"💰 Стоимость: <b>{draft.total_price} ₽</b>\n" if draft.total_price is not None else ""
    return (
        "✅ <b>Заявка на аренду отправлена!</b>\n\n"
        f"📦 <b>{_safe(item.title)}</b>\n"
        f"Количество: <b>{draft.quantity or 1}</b>\n"
        f"⏱️ Ориентировочный срок аренды: <b>{_safe(draft.rental_period_text)}</b>\n"
        #f"{price_line}"
        "ℹ️ Статус: <b>Ожидает обработки менеджером</b>\n\n"
        "Вы получите уведомление, когда менеджер обработает вашу заявку."
    )

# def format_rent_details_request_text(item: ItemOut, period_text: str) -> str:
#     """Текст запроса дополнительных деталей аренды одним сообщением."""
#     return (
#         f"🤝 <b>Заявка на аренду</b>\n\n"
#         f"Вы собираетесь арендовать: <b>{item.title}</b>\n"
#         f"⏱️ Выбранный срок: <b>{period_text}</b>\n\n"
#         "Напишите в одном сообщении:\n"
#         "<b>Кол-во дней аренды - К какому дню вам нужен товар (дата) - "
#         "Любое сообщение, которое хотите нам отправить/уточнить</b>\n\n"
#         "Например: <code>3 - 25.06.2026 - Нужна доставка вечером</code>"
#     )