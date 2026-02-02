ACTIVE = "ACTIVE"
BANNED = "BANNED"

_ALLOWED_TRANSITIONS = {
    ACTIVE: {BANNED},
    BANNED: {ACTIVE},
}

def can_transition(old_status: str, new_status: str) -> bool:
    return new_status in _ALLOWED_TRANSITIONS.get(old_status, set())
