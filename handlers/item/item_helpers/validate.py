from decimal import Decimal, InvalidOperation

# ─────────────────────────────────────────────────flow_create──────────────────────────────────────────────────────────
def validate_item_title(title: str) -> str | None:
    if not title:
        return "❌ Название не должно быть пустым. Введите название вещи."
    if len(title) < 3:
        return "❌ Название слишком короткое. Введите не менее 3 символов."
    if len(title) > 255:
        return "❌ Название слишком длинное. Введите не более 255 символов."
    return None

# тут проверь
def validate_item_description(description: str) -> str | None:
    if not description:
        return "❌ Описание не должно быть пустым. Введите описание вещи."

    elif len(description) < 10:
        return "❌ Описание слишком короткое. Пожалуйста, введите более подробное описание (минимум 10 символов)"

    return None # ?

def validate_item_price(price_text: str) -> tuple[str | None, Decimal | None]:
    try:
        price = Decimal(price_text)
    except (InvalidOperation, ValueError):
        return "❌ Некорректное значение.\nВведите цену — только число, больше 0.", None

    if price <= 0:
        return "❌ Цена должна быть положительным числом.", None

    return None, price

def validate_item_deposit(deposit_text: str) -> tuple[str | None, Decimal | None]:
    try:
        deposit = Decimal(deposit_text)
    except (InvalidOperation, ValueError):
        return "❌ Некорректное значение. Пожалуйста, введите число.", None

    if deposit < 0:
        return "❌ Сумма залога не может быть отрицательной.", None

    return None, deposit

def validate_item_min_period(rental_period: str) -> tuple[str | None, int | None]:
    try:
        min_days = int(rental_period)
    except ValueError:
        return "❌ Некорректное значение. Введите число дней, например: <code>1</code>.", None

    if min_days < 1:
        return "❌ Минимальный срок аренды должен быть не меньше 1 дня.", None

    return None, min_days

def short_description(description: str | None, limit: int = 300) -> str:
    if not description:
        return "Описание не указано"

    cleaned = description.strip()
    if len(cleaned) <= limit:
        return cleaned

    return cleaned[: limit - 3].rstrip() + "..." # не проверял

def extract_item_confirmation_context(data: dict) -> tuple[str, str, list[str]]:
    category_name = data.get("selected_category_name") or "будет уточнена модератором"
    subcategory_name = data.get("selected_subcategory_name") or "будет уточнена модератором"

    raw_photos: list[str] = data.get("photos") or []
    photos = [photo for photo in raw_photos if isinstance(photo, str) and photo.strip()]

    return category_name, subcategory_name, photos