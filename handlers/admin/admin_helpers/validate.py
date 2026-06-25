from status.item_status import ItemStatus

def parse_admin_item_status(raw_status: str | None) -> ItemStatus:
    """Распарсить статус товара из admin callback data"""
    if not raw_status:
        return ItemStatus.DRAFT

    #normalized = raw_status.strip()
    try:
        return ItemStatus(raw_status) # normalized = raw_status.strip()
    except ValueError:
        return ItemStatus.DRAFT

# Как он работает
# parse_admin_item_status("DRAFT") # ItemStatus.DRAFT
# parse_admin_item_status("ACTIVE") # ItemStatus.ACTIVE
# parse_admin_item_status("BAD_STATUS") # ItemStatus.DRAFT
