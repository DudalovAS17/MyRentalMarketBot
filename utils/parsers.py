import re
from decimal import Decimal, InvalidOperation


def money_from_text(value: str | None) -> Decimal | None:
    """Достать первое денежное значение из текстового фрагмента."""
    if not value:
        return None

    match = re.search(r"(\d[\d\s]*(?:[,.]\d+)?)", value)
    if not match:
        return None

    try:
        return Decimal(match.group(1).replace(" ", "").replace(",", ".")).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return None

def parse_period_prices(price_text: str | None) -> dict[str, Decimal]:
    """Распарсить цены по диапазонам из описания цены товара."""
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
        price = money_from_text(match.group(1))
        if price is not None:
            prices[code] = price
    return prices
