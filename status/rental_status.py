import enum

# ───────────────────────────────────────────── enum ───────────────────────────────────────────────────────────────────
class RentalActorRole(enum.Enum):
    """Роль текущего пользователя в сделке аренды"""
    OWNER = "owner"
    RENTER = "renter"

class RentalStatus(enum.Enum):
    """Статусы жизненного цикла сделки аренды"""
    REQUESTED = "requested"
    CONFIRMED = "confirmed"
    ACTIVE = "active"
    COMPLETED = "completed"

    REJECTED_BY_OWNER = "rejected_by_owner"
    REJECTED_BY_RENTER = "rejected_by_renter"
    CANCELLED_CONFIRMED_BY_OWNER = "cancelled_confirmed_by_owner"
    CANCELLED_CONFIRMED_BY_RENTER = "cancelled_confirmed_by_renter"
    CANCELLED_BY_OWNER = "cancelled_by_owner"
    CANCELLED_BY_RENTER = "cancelled_by_renter"

    DISPUTED = "disputed"

# ───────────────────────────────────────── helper-функции ─────────────────────────────────────────────────────────────
def is_terminal_status(status: RentalStatus) -> bool:
    """True если статус терминальный (сделка завершена)"""
    return status in TERMINAL_STATUSES

def is_open_status(status: RentalStatus) -> bool:
    """True если статус open (сделка активна/жива и блокирует вещь)"""
    return status in OPEN_STATUSES

def open_statuses() -> tuple[RentalStatus, ...]:
    """Стабильный список open-статусов (удобно для .in_(...))."""
    return tuple(OPEN_STATUSES)

# ───────────────────────────────────── классификация статусов ─────────────────────────────────────────────────────────
TERMINAL_STATUSES: frozenset[RentalStatus] = frozenset({
        RentalStatus.COMPLETED,
        RentalStatus.REJECTED_BY_OWNER,
        RentalStatus.REJECTED_BY_RENTER,
        RentalStatus.CANCELLED_CONFIRMED_BY_OWNER,
        RentalStatus.CANCELLED_CONFIRMED_BY_RENTER,
        RentalStatus.CANCELLED_BY_OWNER,
        RentalStatus.CANCELLED_BY_RENTER,
    })

OPEN_STATUSES: frozenset[RentalStatus] = frozenset({
        RentalStatus.REQUESTED,
        RentalStatus.CONFIRMED,
        RentalStatus.ACTIVE,
        RentalStatus.DISPUTED,
    })

# ─────────────────────────────────────────── UI-лейблы ────────────────────────────────────────────────────────────────
STATUS_LABELS: dict[RentalStatus, str]  = {
    RentalStatus.REQUESTED: "Запрос отправлен",
    RentalStatus.CONFIRMED: "Подтверждена (ожидает передачи)",
    RentalStatus.ACTIVE: "Активна (вещь передана)",
    RentalStatus.COMPLETED: "Завершена",
    RentalStatus.CANCELLED_BY_OWNER: "Отменена владельцем",
    RentalStatus.CANCELLED_BY_RENTER: "Отменена арендатором",
    RentalStatus.REJECTED_BY_OWNER: "Отклонена владельцем",
    RentalStatus.REJECTED_BY_RENTER: "Отклонена арендатором",
    RentalStatus.DISPUTED: "⚠️ <b>Спор открыт</b>. Дальнейшие действия по сделке заблокированы до решения",
    RentalStatus.CANCELLED_CONFIRMED_BY_OWNER: "Отменена владельцем (до передачи)",
    RentalStatus.CANCELLED_CONFIRMED_BY_RENTER: "Отменена арендатором (до получения)",
}