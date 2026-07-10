from schemas.item import ItemOut
from status.item_status import ItemStatus


def can_request_item(item: ItemOut, *, has_open_rental: bool = False) -> bool:
    """Return True when a client may start a rental request for this item."""
    return (
        item.status == ItemStatus.ACTIVE
        and item.available_quantity > 0
        and not has_open_rental
    )


def item_unavailable_text(
    item: ItemOut,
    *,
    has_open_rental: bool = False,
    busy_until: str | None = None,
) -> str:
    """Build a short user-facing reason why the rental request is unavailable."""
    if item.status != ItemStatus.ACTIVE:
        return "⛔ Сейчас недоступно"

    if item.available_quantity <= 0:
        return "⛔ Нет в наличии"

    if has_open_rental:
        return f"⛔ Сейчас занято (до {busy_until})" if busy_until else "⛔ Сейчас занято"

    return "⛔ Сейчас недоступно"