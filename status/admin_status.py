import enum
from enum import StrEnum

class AdminActionType(enum.Enum):
    """Типы действий администратора для audit-записей"""

    CREATE_ITEM = "create_item"
    UPDATE_ITEM = "update_item"
    HIDE_ITEM = "hide_item"
    ARCHIVE_ITEM = "archive_item"

    TAKE_RENTAL_IN_PROGRESS = "take_rental_in_progress"
    CONFIRM_RENTAL = "confirm_rental"
    REJECT_RENTAL = "reject_rental"
    CANCEL_RENTAL = "cancel_rental"
    COMPLETE_RENTAL = "complete_rental"
    ADMIN_CANCEL_RENTAL = "admin_cancel_rental"

    CLOSE_SUPPORT_TICKET = "close_support_ticket"

    #№RESOLVE_DISPUTE = "RESOLVE_DISPUTE"

    BAN_USER = "ban_user"
    UNBAN_USER = "unban_user"


class AdminEntityType(str, enum.Enum):
    """Типы сущностей, с которыми работает администратор"""
    RENTAL = "rental"
    ITEM = "item"
    USER = "user"
    ADMIN = "admin"
    SUPPORT_TICKET = "support_ticket"


class AdminRole(StrEnum):
    """Роли сотрудников"""
    OWNER = "owner" # владелец системы, полный доступ
    ADMIN = "admin" # управление каталогом, заявками, настройками
    MANAGER = "manager" # обработка заявок и поддержка

# ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────