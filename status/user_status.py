import enum

class AccountStatus(enum.Enum):
    """Статусы состояния аккаунта пользователя"""
    ACTIVE = "ACTIVE"
    BLOCKED = "BLOCKED"
    BANNED = "BANNED"


ALLOWED_STATUS_TRANSITIONS: dict[AccountStatus, frozenset[AccountStatus]] = {
    AccountStatus.ACTIVE: frozenset({AccountStatus.BANNED}),
    AccountStatus.BANNED: frozenset({AccountStatus.ACTIVE})
}


def can_transition(old_status: AccountStatus, new_status: AccountStatus) -> bool:
    """Проверить, разрешён ли переход аккаунта из old_status в new_status"""
    return new_status in ALLOWED_STATUS_TRANSITIONS.get(old_status, frozenset())