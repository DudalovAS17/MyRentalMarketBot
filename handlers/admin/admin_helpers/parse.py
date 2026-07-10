from aiogram.types import CallbackQuery

from status.item_status import ItemStatus

# ──────────────────────────────────────────────────   ─────────────────────────────────────────────────────────────
def parse_admin_item_status(raw_status: str | None) -> ItemStatus:
    """Распарсить статус товара из admin callback data

    # Как он работает
        # parse_admin_item_status("DRAFT") # ItemStatus.DRAFT
        # parse_admin_item_status("ACTIVE") # ItemStatus.ACTIVE
        # parse_admin_item_status("BAD_STATUS") # ItemStatus.DRAFT
    """
    if not raw_status:
        return ItemStatus.DRAFT

    #normalized = raw_status.strip()
    try:
        return ItemStatus(raw_status) # normalized = raw_status.strip()
    except ValueError:
        return ItemStatus.DRAFT

# ──────────────────────────────────────────────────   ─────────────────────────────────────────────────────────────
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

# ────────────────────────────────────────────────── items moderation ──────────────────────────────────────────────────
async def get_admin_item_id_or_alert(callback: CallbackQuery) -> int | None:
    """Получить item_id из callback data или показать alert"""
    try:
        return int((callback.data or "").split(":")[-1])
    except (ValueError, IndexError):
        await callback.answer("Некорректный ID товара", show_alert=True)
        return None

# ────────────────────────────────────────────────── users ─────────────────────────────────────────────────────────────
def parse_admin_user_id(raw_text: str | None) -> int | None:
    """Распарсить user_id из текстового ввода"""
    if not raw_text:
        return None

    try:
        return int(raw_text.strip())
    except ValueError:
        return None

async def get_admin_user_id_or_alert(callback: CallbackQuery) -> int | None:
    """Получить user_id из callback data или показать alert"""
    try:
        return int((callback.data or "").split(":")[-1])
    except (ValueError, IndexError):
        await callback.answer("Некорректный user-ID", show_alert=True)
        return None

# ───────────────────────────────────────────────── support ────────────────────────────────────────────────────────────
def parse_support_page(raw: str | None, *, default: int = 1) -> tuple[str, int]:
    """Распарсить тип и номер страницы из callback data поддержки."""
    parts = (raw or "").split(":")
    try:
        kind = parts[-2]
        page = int(parts[-1])
    except (ValueError, IndexError):
        return "items", default

    if kind not in {"items", "rentals", "general"}:
        kind = "items"
    return kind, max(1, page)


def parse_support_ticket_id(raw: str | None) -> int | None:
    """Распарсить ticket_id из callback data поддержки"""
    try:
        return int((raw or "").split(":")[-1])
    except (ValueError, IndexError):
        return None