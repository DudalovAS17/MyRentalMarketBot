
def parse_admin_page(raw: str | None, *, default: int = 1) -> int:
    """Распарсить номер страницы из admin callback data"""
    try:
        page = int((raw or "").split(":")[-1])
    except (ValueError, IndexError):
        return default
    return max(1, page)

def parse_admin_rental_id(raw: str | None) -> int | None:
    """Распарсить rental_id из admin callback data"""
    try:
        return int((raw or "").split(":")[-1])
    except (ValueError, IndexError):
        return None

def parse_admin_rental_id_text(raw: str | None) -> int | None:
    """Распарсить rental_id из текстового ввода админа"""
    try:
        return int((raw or "").strip())
    except (ValueError, TypeError):
        return None