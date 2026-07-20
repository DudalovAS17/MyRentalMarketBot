import re
from aiogram.types import CallbackQuery

from handlers.rentals.rental_helpers.keyboard import PERIOD_LABELS, RENT_PERIOD_CB


CUSTOM_DATES_RE = re.compile(r"^\s*(\d{2}\.\d{2}\.\d{4})\s*[-—–]\s*(\d{2}\.\d{2}\.\d{4})\s*$")
# ──────────────────────────────────────── PARSE ───────────────────────────────────────────────────────────────────────
def parse_rent_item_id(data: str | None) -> int | None:
    """Распарсить item_id из callback data начала аренды"""
    if not data:
        return None

    try:
        raw_value = data.split(":", 1)[1]
        return int(raw_value)
    except (IndexError, ValueError):
        return None

def parse_rental_id(data: str | None) -> int | None:
    """Распарсить rental_id из callback data действия заявки.

    Ожидаем формат жёсткий формат: ["rental_action", "confirm", "<id>"]"""
    if not data:
        return None

    try:
        _, _, raw_rental_id = data.split(":", 2)
        return int(raw_rental_id)
    except (IndexError, ValueError):
        return None

def parse_custom_days_text(text: str | None) -> int | None:
    """Распарсить количество дней аренды из сообщения пользователя."""
    if not text:
        return None

    value = text.strip()
    if not value.isdigit():
        return None

    days = int(value)
    return days if days >= 1 else None

async def get_rental_id_or_alert(callback: CallbackQuery) -> int | None:
    """Получить rental_id из callback data или показать alert"""
    rental_id = parse_rental_id(callback.data)

    if rental_id is None:
        await callback.answer("Некорректная кнопка.", show_alert=True)
        return None

    return rental_id

# ?
def parse_rent_details_message(text: str | None) -> tuple[int, str, str | None] | None:
    """Распарсить одно сообщение: кол-во дней - дата, к которой нужен товар - комментарий."""
    if not text:
        return None

    parts = [part.strip() for part in re.split(r"\s*[-—–]\s*", text.strip(), maxsplit=2)]
    if len(parts) < 2 or not parts[0].isdigit() or not parts[1]:
        return None

    days = int(parts[0])
    if days < 1:
        return None

    comment = parts[2] if len(parts) == 3 and parts[2] else None
    return days, parts[1], comment


# ──────────────────────────────────────────── for Rental FSM ──────────────────────────────────────────────────────────
def parse_positive_int(text: str | None) -> int | None:
    """Распарсить положительное целое число из пользовательского текста."""
    if not text:
        return None
    value = text.strip()
    if not value.isdigit():
        return None
    parsed = int(value)
    return parsed if parsed >= 1 else None

def parse_rent_quantity_code(data: str | None) -> int | None:
    """Распарсить количество из callback выбора количества."""
    from utils.callbacks import RENT_QUANTITY_CB

    if not data or not data.startswith(RENT_QUANTITY_CB):
        return None
    raw = data.removeprefix(RENT_QUANTITY_CB)
    if raw == "manual":
        return None
    return parse_positive_int(raw)

def parse_rent_period_code(data: str | None) -> str | None:
    """Распарсить код фиксированного диапазона аренды."""
    if not data or not data.startswith(RENT_PERIOD_CB):
        return None
    code = data.removeprefix(RENT_PERIOD_CB)
    return code if code in PERIOD_LABELS else None

def parse_delivery_choice(data: str | None) -> bool | None:
    """Распарсить выбор доставки из callback."""
    from utils.callbacks import RENT_DELIVERY_CB

    if not data or not data.startswith(RENT_DELIVERY_CB):
        return None
    raw = data.removeprefix(RENT_DELIVERY_CB)
    if raw == "yes":
        return True
    if raw == "no":
        return False
    return None

def normalize_phone(text: str | None) -> str | None:
    """Нормализовать телефон клиента к формату с плюсом или вернуть None."""
    if not text:
        return None
    value = text.strip()
    digits = re.sub(r"\D", "", value)
    if len(digits) < 10 or len(digits) > 15:
        return None
    if value.startswith("+"):
        return "+" + digits
    if len(digits) == 11 and digits.startswith("8"):
        return "+7" + digits[1:]
    if len(digits) == 10:
        return "+7" + digits
    return "+" + digits

def is_rent_draft_complete(draft) -> bool:
    """Проверить, что FSM-draft содержит все обязательные поля заявки."""
    return bool(
        draft.item_id
        and draft.quantity
        and draft.quantity >= 1
        and draft.rental_period_text
        and draft.delivery_needed is not None
        and (not draft.delivery_needed or draft.delivery_address)
        and draft.client_name
        and draft.client_phone
    )