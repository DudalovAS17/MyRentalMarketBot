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