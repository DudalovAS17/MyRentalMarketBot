import re

# ────────────────────────────────────────────────── edit profile ──────────────────────────────────────────────────────
EMAIL_REGEX = r"[^@]+@[^@]+\.[^@]+"
def is_valid_email(email: str) -> bool:
    """Проверить email на базовый корректный формат."""
    return bool(re.match(EMAIL_REGEX, email))


def validate_profile_name(name: str) -> str | None:
    """Проверить новое имя пользователя."""
    if not name:
        return "⚠️ Имя не может быть пустым. Пожалуйста, введите имя."

    if len(name) < 2:
        return "⚠️ Имя слишком короткое. Введите минимум 2 символа."

    if len(name) > 80:
        return "⚠️ Имя слишком длинное. Введите не более 80 символов."

    return None

def validate_profile_email(email: str) -> str | None:
    """Проверка корректности нового email пользователя."""
    if not email:
        return "⚠️ Email не может быть пустым. Введите email."

    if not is_valid_email(email):
        return (
            "⚠️ Пожалуйста, введите корректный email.\n"
            "Пример: example@mail.com"
        )

    return None

# ────────────────────────────────────────────────── phone ─────────────────────────────────────────────────────────────
def is_own_contact(contact, tg_user) -> bool:
    """Проверить, что контакт принадлежит текущему Telegram-пользователю."""
    return bool(contact and tg_user and contact.user_id == tg_user.id)

def normalize_profile_phone(raw_phone: str | None) -> str | None:
    """Нормализовать телефон профиля для MVP-контактов."""
    if not raw_phone:
        return None

    cleaned = re.sub(r"[^0-9+]", "", raw_phone.strip())
    if cleaned.startswith("8") and len(cleaned) == 11:
        cleaned = "+7" + cleaned[1:]
    elif cleaned.startswith("7") and len(cleaned) == 11:
        cleaned = "+" + cleaned

    digits = re.sub(r"\D", "", cleaned)
    if len(digits) < 10 or len(digits) > 15:
        return None
    if cleaned.startswith("+"):
        return "+" + digits
    return cleaned