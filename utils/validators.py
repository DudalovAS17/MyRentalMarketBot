from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Optional
from utils.errors import ValidationError


# ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
def ui_str(value: Optional[str], default: str = "-") -> str:
    return value if value else default

def ui_money(value: Optional[Decimal], default: str = "0") -> str:
    return str(value) if value is not None else default

def ui_int(value: Optional[int], default: int = 0) -> int:
    return value if value is not None else default

# Красивое имя вида: "Александр С. (@potch)"
def fmt_person(name: str, username: str = None) -> str:
    return f"{name} (@{username})" if username else name

# ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
def validate_name(name: str) -> str:
    """Нормализует и валидирует непустое название категории."""
    normalized = name.strip()
    if not normalized:
        raise ValidationError("Название категории не может быть пустым")
    return normalized

def parse_callback(data: str | None, prefix: str) -> int | None:
    """Возвращает целое число после ``prefix`` или ``None`` для некорректных данных."""
    if not data or not data.startswith(prefix):
        return None

    try:
        return int(data[len(prefix):])
    except (TypeError, ValueError):
        return None


# ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
# def format_price(price: int | float) -> str:
#     return f"{price:,.2f}".replace(",", " ").replace(".00", "")

# разбери
def format_price(price: int | float | Decimal | str | None) -> str:
    """
    Форматирует цену:
    - разделители тысяч пробелом
    - 2 знака после запятой (если они не нули — показываем, иначе убираем)
    Примеры: 12000 -> "12 000", Decimal("12.50") -> "12.5", Decimal("12.00") -> "12"
    """
    if price is None:
        return "—"

    try:
        d = price if isinstance(price, Decimal) else Decimal(str(price))
    except (InvalidOperation, ValueError, TypeError):
        return "—"

    # Денежное округление до копеек
    d = d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    # Строка без экспоненты
    s = format(d, "f")

    # Убираем хвостовые нули и точку, если стало целым
    if "." in s:
        s = s.rstrip("0").rstrip(".")

    # Добавляем разделители тысяч
    if "." in s:
        int_part, frac_part = s.split(".", 1)
        int_part = f"{int(int_part):,}".replace(",", " ")
        return f"{int_part}.{frac_part}"
    else:
        return f"{int(s):,}".replace(",", " ")

def format_days(n: int) -> str:
    """Возвращает правильную русскую форму слова для количества дней."""
    if n % 10 == 1 and n % 100 != 11: # n % 10 == 1 (последняя цифра = 1) пропускает 1, (11), 21, 31, 101
        return "день"
    if 2 <= n % 10 <= 4 and not (12 <= n % 100 <= 14):
        return "дня"
    return "дней"

def format_step(title: str, step: int, total: int) -> str:
    """Возвращает форматированный заголовок с прогрессом"""
    progress = f"<b>Шаг {step} из {total}</b>\n\n"
    return f"{progress}{title}"