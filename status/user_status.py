import enum

class AccountStatus(enum.Enum):
    """Статус аккаунта пользователя или сотрудника компании.

    Используется для базового контроля доступа:
    активный аккаунт может пользоваться ботом, заблокированный — нет."""

    ACTIVE = "ACTIVE" # клиент/админ может пользоваться ботом
    BANNED = "BANNED" # доступ заблокирован админом


ALLOWED_STATUS_TRANSITIONS: dict[AccountStatus, frozenset[AccountStatus]] = {
    AccountStatus.ACTIVE: frozenset({AccountStatus.BANNED}),
    AccountStatus.BANNED: frozenset({AccountStatus.ACTIVE})
}


def can_transition(old_status: AccountStatus, new_status: AccountStatus) -> bool:
    """Проверить, разрешён ли переход аккаунта из old_status в new_status"""
    return new_status in ALLOWED_STATUS_TRANSITIONS.get(old_status, frozenset())