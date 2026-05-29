import enum
from enum import StrEnum
from status.rental_status import RentalStatus

# ───────────────────────────────────────────── enum ───────────────────────────────────────────────────────────────────
class AdminActionType(str, enum.Enum):
    """Типы действий администратора для audit-записей"""
    ADMIN_CANCEL_RENTAL = "ADMIN_CANCEL_RENTAL"
    RESOLVE_DISPUTE = "RESOLVE_DISPUTE"
    BAN_USER = "BAN_USER"
    UNBAN_USER = "UNBAN_USER"

class AdminEntityType(str, enum.Enum):
    """Типы сущностей, с которыми работает администратор"""
    RENTAL = "rental"
    ITEM = "item"
    USER = "user"
    COMPLAINT = "complaint"
    SUPPORT_TICKET = "support_ticket"

class AdminRole(StrEnum):
    OWNER = "owner" # владелец системы, полный доступ
    ADMIN = "admin" # управление каталогом, заявками, настройками
    MANAGER = "manager" # обработка заявок и поддержка

# ───────────────────────────────────── классификация статусов ─────────────────────────────────────────────────────────
CANCEL_STATUS_MAP = {
    RentalStatus.REQUESTED: RentalStatus.REJECTED_BY_OWNER, # REQUESTED → REJECTED_BY_OWNER
    RentalStatus.CONFIRMED: RentalStatus.CANCELLED_CONFIRMED_BY_OWNER,
    RentalStatus.ACTIVE: RentalStatus.CANCELLED_BY_OWNER,
    RentalStatus.DISPUTED: RentalStatus.CANCELLED_BY_OWNER,
}

ALLOWED_TARGETS = {RentalStatus.ACTIVE, RentalStatus.COMPLETED, RentalStatus.CONFIRMED}