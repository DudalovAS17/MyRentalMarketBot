import re
from aiogram.types import CallbackQuery, Message
from decimal import Decimal, InvalidOperation

from handlers.rentals.rental_helpers.texts import item_not_available_message
from handlers.rentals.rental_helpers.keyboard import PERIOD_LABELS, RENT_PERIOD_CB
from services.rental_service import RentalService

from schemas.item import ItemOut
from utils.domain_exceptions import ItemNotAvailable
from utils.item_availability import can_request_item, item_unavailable_text

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
    """Распарсить rental_id из callback data действия сделки.

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

def _money_from_text(value: str) -> Decimal | None:
    """Достать первое денежное значение из текстового фрагмента."""
    match = re.search(r"(\d[\d\s]*(?:[,.]\d+)?)", value)
    if not match:
        return None

    try:
        return Decimal(match.group(1).replace(" ", "").replace(",", ".")).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return None

def parse_period_prices(price_text: str | None) -> dict[str, Decimal]:
    """Распарсить цены по диапазонам из человеко-читаемого текста цены товара."""
    if not price_text:
        return {}

    normalized = price_text.lower().replace("ё", "е")
    patterns = {
        "1d": r"(?:сутки|1\s*(?:день|дн|сут))\D*(\d[\d\s]*(?:[,.]\d+)?)",
        "2_7d": r"2\s*[-–—]\s*7\s*(?:дн|сут|дней)?\D*(\d[\d\s]*(?:[,.]\d+)?)",
        "8_14d": r"8\s*[-–—]\s*14\s*(?:дн|сут|дней)?\D*(\d[\d\s]*(?:[,.]\d+)?)",
        "15_plus": r"(?:>|от)?\s*15\+?\s*(?:дн|сут|дней)?\D*(\d[\d\s]*(?:[,.]\d+)?)",
    }

    prices: dict[str, Decimal] = {}
    for code, pattern in patterns.items():
        match = re.search(pattern, normalized)
        if not match:
            continue
        price = _money_from_text(match.group(1))
        if price is not None:
            prices[code] = price

    return prices

""" Более строгий парсе id сделки
async def _parse_accessible_rental_id(
    callback: CallbackQuery,
    rental_service: RentalService,
    user,
    prefix: str,
) -> int | None:
    ""Получить rental_id из callback и проверить доступ клиента к заявке.""
    rental_id = parse_callback(callback.data, prefix)
    if rental_id is None:
        await callback.answer("Некорректная заявка.", show_alert=True)
        return None

    try:
        details = await rental_service.get_rental_details(rental_id=rental_id, current_user_id=user.id)
    except ServiceError:
        await callback.answer("Ошибка. Попробуйте позже.", show_alert=True)
        return None

    if not details:
        await callback.answer("Заявка не найдена или нет доступа.", show_alert=True)
        return None

    return rental_id
"""
# ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
async def abort_if_item_unavailable(event: CallbackQuery | Message, rental_service: RentalService, item: ItemOut) -> bool:
    """Вернуть True, если rent-flow нужно остановить из-за недоступности товара."""

    message = event.message if isinstance(event, CallbackQuery) else event

    if not can_request_item(item):
        if message:
            await message.answer(item_unavailable_text(item))
        return True

    try:
        await rental_service.ensure_item_available(item.id)
    except ItemNotAvailable:
        message = event.message if isinstance(event, CallbackQuery) else event
        if message:
            await message.answer(item_not_available_message)
        return True

    return False

# ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
def calculate_total_rent_price(price_per_day: Decimal | int | float, days: int) -> tuple[Decimal, Decimal]:
    """Рассчитать цену за день и итоговую стоимость аренды"""
    normalized_price = price_per_day if isinstance(price_per_day, Decimal) else Decimal(str(price_per_day))
    total_rent_price = (normalized_price * Decimal(days)).quantize(Decimal("0.01"))
    return normalized_price, total_rent_price

def calculate_price_for_fixed_period_total(
    item_price: Decimal | int | float,
    period_code: str,
    price_text: str | None = None,
) -> Decimal | None:
    """Получить готовую цену для выбранного диапазона."""
    period_prices = parse_period_prices(price_text)
    if period_code in period_prices:
        return period_prices[period_code]

    return item_price if isinstance(item_price, Decimal) else Decimal(str(item_price)).quantize(Decimal("0.01"))

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

def is_quantity_available(quantity: int, available_quantity: int | None) -> bool:
    """Проверить, что выбранное количество положительное и не превышает доступное."""
    return quantity >= 1 and (available_quantity is None or quantity <= available_quantity)

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