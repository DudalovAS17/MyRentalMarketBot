import enum

class AccountStatus(enum.Enum):
    ACTIVE = "ACTIVE"
    BLOCKED = "BLOCKED"
    BANNED = "BANNED"

# ALLOWED_STATUS_TRANSITIONS: dict[AccountStatus, set[AccountStatus]] = {
#     AccountStatus.ACTIVE: {AccountStatus.BANNED},
#     AccountStatus.BANNED: {AccountStatus.ACTIVE}
# }

ALLOWED_STATUS_TRANSITIONS: dict[AccountStatus, frozenset[AccountStatus]] = {
 AccountStatus.ACTIVE: frozenset({AccountStatus.BANNED}),
 AccountStatus.BANNED: frozenset({AccountStatus.ACTIVE})
}

def can_transition(old_status: AccountStatus, new_status: AccountStatus) -> bool:
    return new_status in ALLOWED_STATUS_TRANSITIONS.get(old_status, frozenset())