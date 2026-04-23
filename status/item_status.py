import enum

class ItemStatus(enum.Enum):
    ACTIVE = "ACTIVE"
    PENDING = "PENDING"
    REJECTED = "REJECTED"
    HIDDEN = "HIDDEN"

ALLOWED_STATUS_TRANSITIONS: dict[ItemStatus, set[ItemStatus]] = {
    ItemStatus.PENDING: {ItemStatus.ACTIVE, ItemStatus.REJECTED},
    ItemStatus.ACTIVE: {ItemStatus.HIDDEN},
    ItemStatus.HIDDEN: {ItemStatus.ACTIVE},
    ItemStatus.REJECTED: set(),
}

#ALLOWED_STATUS_TRANSITIONS: dict[ItemStatus, frozenset[ItemStatus]] = {
#    ItemStatus.PENDING: frozenset({ItemStatus.ACTIVE, ItemStatus.REJECTED}),
#    ItemStatus.ACTIVE: frozenset({ItemStatus.HIDDEN}),
#    ItemStatus.HIDDEN: frozenset({ItemStatus.ACTIVE}),
#    ItemStatus.REJECTED: frozenset(),
#}

def can_transition(old_status: ItemStatus, new_status: ItemStatus) -> bool:
    """Проверить, разрешён ли переход объявления из old_status в new_status"""
    return new_status in ALLOWED_STATUS_TRANSITIONS.get(old_status, set())
