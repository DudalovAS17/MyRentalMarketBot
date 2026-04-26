from dataclasses import dataclass
from enum import StrEnum

from schemas.user import UserOut
from status.user_status import AccountStatus


class StartAction(StrEnum):
    REGISTER = "register"
    ACCESS_BLOCKED = "access_blocked"
    MAIN_MENU = "main_menu"


@dataclass(slots=True)
class StartEntryResult:
    action: StartAction
    user: UserOut | None = None


def can_use_bot(status: AccountStatus) -> bool:
    """Проверить, может ли пользователь пользоваться ботом"""
    return status == AccountStatus.ACTIVE