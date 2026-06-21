import re
from aiogram.types import CallbackQuery, Message
from decimal import Decimal

from handlers.rentals.rental_helpers.texts import item_not_available_message
from handlers.rentals.rental_helpers.keyboard import PERIOD_DAYS, PERIOD_LABELS, RENT_PERIOD_CB
from services.rental_service import RentalService

from utils.domain_exceptions import ItemNotAvailable


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

def parse_rent_period_code(data: str | None) -> str | None:
    """Распарсить код фиксированного диапазона аренды."""
    if not data or not data.startswith(RENT_PERIOD_CB):
        return None
    code = data.removeprefix(RENT_PERIOD_CB)
    return code if code in PERIOD_LABELS else None

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

# ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
async def ensure_rent_item_available_or_notify(event: CallbackQuery | Message, rental_service: RentalService, item_id: int) -> bool:
    """Проверить доступность товара и показать понятное сообщение, если товар занят."""
    try:
        await rental_service.ensure_item_available(item_id)
    except ItemNotAvailable:
        message = event.message if isinstance(event, CallbackQuery) else event
        await message.answer(item_not_available_message)
        return True

    return False

# ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
def calculate_total_rent_price(price_per_day: Decimal | int | float, days: int) -> tuple[Decimal, Decimal]:
    """Рассчитать цену за день и итоговую стоимость аренды"""
    normalized_price = price_per_day if isinstance(price_per_day, Decimal) else Decimal(str(price_per_day))
    total_rent_price = (normalized_price * Decimal(days)).quantize(Decimal("0.01"))
    return normalized_price, total_rent_price

def calculate_fixed_period_total(price_per_day: Decimal | int | float, period_code: str) -> Decimal | None:
    """Рассчитать стоимость для диапазона, если он имеет точное число дней."""
    days = PERIOD_DAYS.get(period_code)
    if days is None:
        return None
    _, total_price = calculate_total_rent_price(price_per_day, days)
    return total_price