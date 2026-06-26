from decimal import Decimal
from aiogram.types import Message

from keyboards.item_kb import cancel_keyboard
from utils.functions import format_step, format_price

# ─────────────────────────────────────────────────show─────────────────────────────────────────────────────────────────
def get_items_count_str(count: int) -> str:
    """Возвращает правильное склонение слова 'объявление'"""
    if count % 10 == 1 and count % 100 != 11:
        return "объявление"
    elif 2 <= count % 10 <= 4 and (count % 100 < 10 or count % 100 >= 20):
        return "объявления"
    else:
        return "объявлений"

def get_days_str(days: int) -> str:
    """Возвращает правильное склонение слова 'день'"""
    if days % 10 == 1 and days % 100 != 11:
        return "день"
    elif 2 <= days % 10 <= 4 and (days % 100 < 10 or days % 100 >= 20):
        return "дня"
    else:
        return "дней"

# ─────────────────────────────────────────────────create ──────────────────────────────────────────────────────────
def extract_item_text_input(message: Message) -> str:
    """Извлечь текстовый ввод пользователя"""
    return (message.text or "").strip()

def extract_item_money_input(message: Message) -> str:
    """Извлечь денежный ввод пользователя и нормализовать десятичный разделитель"""
    return (message.text or "").strip().replace(",", ".") # Преобразуем введённое значение в число

def extract_item_available_quantity_input(message: Message) -> str:
    """Извлечь ввод доступного количества товара."""
    return (message.text or "").strip()

def format_money_value(value: Decimal | int | float | None) -> str:
    """Сформатировать денежное значение для UI"""
    if value is None:
        return format_price(Decimal("0"))
    return format_price(value)

def format_deposit_value(value: Decimal | int | float | None) -> str:
    """Сформатировать значение залога для UI"""
    if not value:
        return "Без залога" # Decimal("0")?
    return f"{format_price(value)} ₽"

def format_photos_count(count: int) -> str:
    """Сформатировать количество фотографий для UI"""
    if count == 0:
        return "нет фото"
    if count == 1:
        return "1 фото"
    if 2 <= count <= 4:
        return f"{count} фото"
    return f"{count} фото"

async def render_create_item_step_message(message: Message, text: str, step: int, total_steps: int = 6) -> None:
    """Отправить сообщение текущего шага создания объявления"""
    await message.answer(
        format_step(text, step, total_steps),
        parse_mode="HTML",
        reply_markup=cancel_keyboard(),
    )