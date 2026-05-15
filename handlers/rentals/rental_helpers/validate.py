from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from datetime import datetime, timezone, time, date
from decimal import Decimal

from handlers.rentals.rental_helpers.texts import format_item_not_available_message, date_err_msg
from services.rental_service import RentalService

from schemas.item import ItemOut
from utils.functions import send_or_edit, abort_rent_flow
from utils.domain_exceptions import ItemNotAvailable


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


async def parse_and_valid_start_date_str(callback: CallbackQuery, state: FSMContext) -> tuple[str, date] | None:
    """Распарсить и проверить дату начала аренды из callback data"""
    try:
        start_str = callback.data.split(":", 1)[1]  # dd.mm.YYYY (12.03.2025)
        start_date = datetime.strptime(start_str, "%d.%m.%Y").date()  # date(2025, 3, 12)
    except (IndexError, ValueError):
        await abort_rent_flow(callback, state, date_err_msg)
        return None

    validation_error = validate_rent_start_date(start_date)
    if validation_error:
        await send_or_edit(callback, validation_error)
        return None

    return start_str, start_date


async def parse_and_validate_end_date(callback: CallbackQuery, state: FSMContext) -> tuple[str, date, int] | None:
    """Распарсить дату окончания и длительность аренды из callback data"""
    try:
        payload = callback.data.split(":", 2) # "end_date:DD.MM.YYYY:<days>" (:12.03.2025:3)
        end_str = payload[1] # "15.03.2025"
        days = int(payload[2]) # 3
        end_date = datetime.strptime(end_str, "%d.%m.%Y").date()
    except (IndexError, ValueError):
        await abort_rent_flow(callback, state, "❌ Некорректная дата окончания.")
        return None

    if days < 1:
        await abort_rent_flow(callback, state, "❌ Некорректная длительность аренды.")
        return None

    return end_str, end_date, days


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


async def get_rental_id_or_alert(callback: CallbackQuery) -> int | None:
    """Получить rental_id из callback data или показать alert"""
    rental_id = parse_rental_id(callback.data)

    if rental_id is None:
        await callback.answer("Некорректная кнопка.", show_alert=True)
        return None

    return rental_id

# ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
async def ensure_rent_item_available_or_notify(callback: CallbackQuery, rental_service: RentalService, item_id: int) -> bool:
    """Доменная проверка доступности (страховка от гонок). Гарантирует или бросает исключение"""
    try:
        await rental_service.ensure_item_available(item_id)
    except ItemNotAvailable as exc:
        await callback.message.answer(format_item_not_available_message(exc))
        return True

    return False

# ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
async def reject_own_item_rent(callback: CallbackQuery, item: ItemOut, user_id: int) -> bool:
    """Показать ранний UX-guard, если пользователь пытается арендовать свою вещь"""
    if item.user_id == user_id:
        await send_or_edit(callback, "Вы не можете арендовать свою собственную вещь.")
        return True

    return False

# ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
def validate_rent_start_date(start_date: date) -> str | None:
    """защита от tampered callback: нельзя выбрать дату начала в прошлом или сегодня"""
    today = datetime.now(timezone.utc).date()
    if start_date <= today:
        return "❌ Дата начала должна быть не раньше завтрашнего дня."
    return None


async def validate_rent_dates(
    callback: CallbackQuery,
    state: FSMContext,
    start_date_str: str,
    end_date_str: str,
    rent_ui_message_id: int | None,
) -> tuple[datetime, datetime, int] | None:
    """Конвертация строк draft в строгие aware datetime"""
    try:
        start_date = datetime.strptime(start_date_str, "%d.%m.%Y").date()
        end_date = datetime.strptime(end_date_str, "%d.%m.%Y").date()
    except ValueError:
        await abort_rent_flow(callback, state,
            "❌ Некорректные даты. Начните заново.",
            rent_ui_message_id=rent_ui_message_id,
        )
        return None

    if end_date <= start_date:
        await send_or_edit(callback, "❌ Дата окончания должна быть позже даты начала.")
        return None

    start_dt = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
    end_dt = datetime.combine(end_date, time.min, tzinfo=timezone.utc)

    days_count = (end_date - start_date).days

    return start_dt, end_dt, days_count


async def validate_rent_period_or_notify(
    callback: CallbackQuery,
    state: FSMContext,
    start_date_str: str,
    end_date: date,
    days: int,
    item: ItemOut,
    rent_ui_message_id: int | None,
) -> int | None: # tuple[date, int] | None
    """Проверить длительность аренды по ограничениям вещи и показать UX-ошибку"""
    try:
        start_date = datetime.strptime(start_date_str, "%d.%m.%Y").date()
    except ValueError:
        await abort_rent_flow(
            callback,
            state,
            "❌ Некорректная дата начала. Начните заново.",
            rent_ui_message_id=rent_ui_message_id,
        )
        return None

    if end_date <= start_date:
        await send_or_edit(callback, "❌ Дата окончания должна быть позже даты начала.")
        return None

    # (опционально) проверим длительность по датам
    actual_days = (end_date - start_date).days
    if actual_days != days:
        days = actual_days

    min_days = item.min_rental_period or 1
    max_days = item.max_rental_period or 30

    if days < min_days:
        await send_or_edit(callback, f"❌ Минимальный срок аренды: {min_days} дн.")
        return None

    if days > max_days:
        await send_or_edit(callback, f"❌ Максимальный срок аренды: {max_days} дн.")
        return None

    return days # start_date

# ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
def calculate_total_rent_price(price_per_day: Decimal | int | float, days: int) -> tuple[Decimal, Decimal]:
    """Рассчитать цену за день и итоговую стоимость аренды"""

    normalized_price = (
        price_per_day
        if isinstance(price_per_day, Decimal)
        else Decimal(str(price_per_day))
    )
    total_rent_price = (normalized_price * Decimal(days)).quantize(Decimal("0.01"))
    return normalized_price, total_rent_price