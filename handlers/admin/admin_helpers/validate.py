from status.item_status import ItemStatus

def parse_admin_item_status(raw_status: str | None) -> ItemStatus:
    """Распарсить admin item status из callback data"""
    if not raw_status:
        return ItemStatus.PENDING

    try:
        return ItemStatus(raw_status)
    except ValueError:
        return ItemStatus.PENDING

# Как он работает
# _parse_admin_item_status("PENDING") # ItemStatus.PENDING
# _parse_admin_item_status("ACTIVE") # ItemStatus.ACTIVE
# _parse_admin_item_status("BAD_STATUS") # ItemStatus.PENDING
