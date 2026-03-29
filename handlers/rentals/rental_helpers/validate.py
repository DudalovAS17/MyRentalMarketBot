from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from datetime import datetime, timezone, time, date
from decimal import Decimal

from handlers.rentals import create_helpers as ch
from services.rental_service import RentalService
from utils.functions import send_or_edit, abort_rent_flow
from utils.domain_exceptions import ItemNotAvailable


def parse_rent_item_id(data: str | None) -> int | None:
    if not data:
        return None

    try:
        return int(data.split(":", 1)[1])
    except (IndexError, ValueError):
        return None


# Проверь, выполняет ли она свою функцию!
# доменная проверка доступности (защита от старых кнопок/гонок) (ДО запуска выбора дат)
# тут не должен быть пользователь (кнопки нет), но это защита от: старых сообщений, параллельных кликов, гонок.
async def ensure_rent_item_available_or_notify(callback: CallbackQuery, rental_service: RentalService, item_id: int) -> bool:
    """Доменная проверка доступности (страховка от гонок). Гарантирует или бросает исключение"""
    try:
        await rental_service.ensure_item_available(item_id)
    except ItemNotAvailable as exc:
        # Recoverable: вещь занята, просто показываем сообщение
        await callback.message.answer(ch.format_item_not_available_message(exc))
        return True # вещь недоступна, сообщение уже показано

    return False # вещь доступна


async def reject_own_item_rent(callback: CallbackQuery, item, user_id: int) -> bool:
    """Guard: нельзя арендовать своё"""
    if item.user_id == user_id:
        # Recoverable: пользователь просто ошибся, FSM не чистим
        await send_or_edit(callback, "Вы не можете арендовать свою собственную вещь.")
        return True

    return False


async def parse_and_valid_start_date_str(callback: CallbackQuery, state: FSMContext) -> tuple[str, date] | None:
    try:
        start_str = callback.data.split(":", 1)[1]  # dd.mm.YYYY (12.03.2025)
        start_date = datetime.strptime(start_str, "%d.%m.%Y").date()  # date(2025, 3, 12)
    except (IndexError, ValueError):
        # Fatal: битый callback-data → завершаем flow
        await abort_rent_flow(callback, state, ch.date_err_msg)
        return None

    validation_error = ch.validate_rent_start_date(start_date)
    if validation_error:
        await send_or_edit(callback, validation_error)
        return None

    return start_str, start_date


def validate_rent_start_date(start_date: date) -> str | None:
    """защита от tampered callback: нельзя выбрать дату начала в прошлом или сегодня"""
    today = datetime.now(timezone.utc).date()
    if start_date <= today:
        return "❌ Дата начала должна быть не раньше завтрашнего дня."
    return None


async def parse_and_validate_end_date(callback: CallbackQuery, state: FSMContext) -> tuple[str, date, int] | None:
    try:
        payload = callback.data.split(":", 2) # "end_date:DD.MM.YYYY:<days>" (:12.03.2025:3)
        end_str = payload[1] # "15.03.2025"
        days = int(payload[2]) # 3
        end_date = datetime.strptime(end_str, "%d.%m.%Y").date()
    except (IndexError, ValueError):
        await abort_rent_flow(callback, state, "❌ Некорректная дата окончания.")
        return None

    if days < 1:
        # Fatal: некорректная длительность (кнопка битая) → завершаем flow
        await abort_rent_flow(callback, state, "❌ Некорректная длительность аренды.")
        return None

    return end_str, end_date, days


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
        # Fatal: даты битые → завершаем flow
        await abort_rent_flow(callback, state,
            "❌ Некорректные даты. Начните заново.",
            rent_ui_message_id=rent_ui_message_id,
        )
        return None

    if end_date <= start_date:
        # Recoverable: логическая ошибка → остаёмся в confirmation
        await send_or_edit(callback, "❌ Дата окончания должна быть позже даты начала.")
        return None

    tz = datetime.now(timezone.utc).astimezone().tzinfo
    start_dt = datetime.combine(start_date, time.min).replace(tzinfo=tz)
    end_dt = datetime.combine(end_date, time.min).replace(tzinfo=tz)

    days_count = (end_date - start_date).days

    return start_dt, end_dt, days_count


async def validate_rent_period_or_notify(
    callback: CallbackQuery,
    state: FSMContext,
    start_date_str: str,
    end_date: date,
    days: int,
    item,
    rent_ui_message_id: int | None,
) -> int | None: # tuple[date, int] | None
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
        # Recoverable: пользователь выбрал “не туда” → остаёмся в шаге end_date (без clear)
        await send_or_edit(callback, "❌ Дата окончания должна быть позже даты начала.")
        return None

    # (опционально) проверим длительность по датам
    actual_days = (end_date - start_date).days
    if actual_days != days:
        # Recoverable: не фейлим, а синхронизируем на фактическое значение
        days = actual_days

    min_days = item.min_rental_period or 1
    max_days = item.max_rental_period or 30

    if days < min_days:
        # Recoverable: коротко → остаёмся на выборе end_date
        await send_or_edit(callback, f"❌ Минимальный срок аренды: {min_days} дн.")
        return None

    if days > max_days:
        # Recoverable: длинно → остаёмся на выборе end_date
        await send_or_edit(callback, f"❌ Максимальный срок аренды: {max_days} дн.")
        return None

    return days # start_date


def calculate_total_rent_price(price_per_day: Decimal | int | float, days: int) -> tuple[Decimal, Decimal] | None:
    # price может быть Decimal — ок. Если вдруг float/int — приведём к Decimal.
    normalized_price = (
        price_per_day
        if isinstance(price_per_day, Decimal)
        else Decimal(str(price_per_day))
    )
    total_rent_price = (normalized_price * Decimal(days)).quantize(Decimal("0.01"))
    return normalized_price, total_rent_price