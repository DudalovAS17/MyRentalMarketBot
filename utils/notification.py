from typing import Optional

def format_new_rental_request(*, item_title: str, renter_username: Optional[str]) -> str:
    renter_display = f"@{renter_username}" if renter_username else "-"

    return (
        "🔔 Новая заявка на аренду\n"
        f"📩 Объявление: {item_title or '—'}\n"
        f"👤 Арендатор: {renter_display}"
    )