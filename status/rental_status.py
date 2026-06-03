import enum

# class RentalActorRole(enum.Enum):
#     """Роль текущего пользователя в сделке аренды"""
#     OWNER = "owner"
#     RENTER = "renter"

class RentalStatus(enum.Enum):
    """Статус заявки клиента на аренду товара.

    Описывает путь заявки от отправки клиентом до обработки менеджером и финального закрытия."""

    REQUESTED = "requested" # аренда уже реально началась / товар выдан клиенту / заявка перешла в фактическое исполнение
    IN_PROGRESS = "in_progress" # заявка в обработке; менеджер уже смотрит наличие и связывается с клиентом
    CONFIRMED = "confirmed" # заявка подтверждена менеджером; условия согласованы, товар зарезервирован/готовится к выдаче
    REJECTED = "rejected" # заявка отклонена менеджером; например, товар недоступен или компания не может выполнить запрос
    COMPLETED = "completed" # заявка завершена; аренда отработана, товар возвращён/услуга закрыта
    CANCELLED_BY_CLIENT = "cancelled_by_client" # заявка отменена клиентом; клиент передумал или отказался от аренды
    CANCELLED_BY_ADMIN = "cancelled_by_admin" # заявка отменена менеджером/админом; например, клиент не отвечает, заявка дубль или условия не согласованы

    # ACTIVE = "active"
    # DISPUTED = "disputed"

# ───────────────────────────────────── классификация статусов ─────────────────────────────────────────────────────────
TERMINAL_STATUSES: frozenset[RentalStatus] = frozenset({
    RentalStatus.REJECTED,
    RentalStatus.CANCELLED_BY_CLIENT,
    RentalStatus.CANCELLED_BY_ADMIN,
    RentalStatus.COMPLETED,
})

OPEN_STATUSES: frozenset[RentalStatus] = frozenset({
        RentalStatus.REQUESTED,
        RentalStatus.IN_PROGRESS,
        RentalStatus.CONFIRMED,
    })


STATUS_LABELS: dict[RentalStatus, str]  = {
    RentalStatus.REQUESTED: "Заявка отправлена",
    RentalStatus.IN_PROGRESS: "В обработке",
    RentalStatus.CONFIRMED: "Подтверждена",
    RentalStatus.REJECTED: "Отклонена",
    RentalStatus.CANCELLED_BY_CLIENT: "Отменена клиентом",
    RentalStatus.CANCELLED_BY_ADMIN: "Отменена менеджером",
    RentalStatus.COMPLETED: "Завершена",

    # RentalStatus.ACTIVE: "Активна",
    # RentalStatus.DISPUTED: "Спор открыт,
}

# ─────────────────────────────────────────── Переходы ─────────────────────────────────────────────────────────────────
ALLOWED_STATUS_TRANSITIONS: dict[RentalStatus, frozenset[RentalStatus]] = {
    RentalStatus.REQUESTED: frozenset({
        RentalStatus.IN_PROGRESS,
        RentalStatus.CONFIRMED,
        RentalStatus.REJECTED,
        RentalStatus.CANCELLED_BY_CLIENT,
        RentalStatus.CANCELLED_BY_ADMIN,
    }),
    RentalStatus.IN_PROGRESS: frozenset({
        RentalStatus.CONFIRMED,
        RentalStatus.REJECTED,
        RentalStatus.CANCELLED_BY_CLIENT,
        RentalStatus.CANCELLED_BY_ADMIN,
    }),
    RentalStatus.CONFIRMED: frozenset({
        RentalStatus.COMPLETED,
        RentalStatus.CANCELLED_BY_CLIENT,
        RentalStatus.CANCELLED_BY_ADMIN,
    }),
    RentalStatus.REJECTED: frozenset(),
    RentalStatus.CANCELLED_BY_CLIENT: frozenset(),
    RentalStatus.CANCELLED_BY_ADMIN: frozenset(),
    RentalStatus.COMPLETED: frozenset(),
}

#№CANCEL_STATUS_MAP = {}
#ALLOWED_TARGETS = {}

# ───────────────────────────────────────── helper-функции ─────────────────────────────────────────────────────────────
def is_terminal_status(status: RentalStatus) -> bool:
    """True, если заявка закрыта и больше не находится в работе."""
    return status in TERMINAL_STATUSES

def is_open_status(status: RentalStatus) -> bool:
    """True, если заявка активна и находится в обработке."""
    return status in OPEN_STATUSES

def open_statuses() -> tuple[RentalStatus, ...]:
    """Стабильный список открытых статусов для запросов к базе. (удобно для .in_(...))."""
    return tuple(OPEN_STATUSES)

def can_transition(old_status: RentalStatus, new_status: RentalStatus) -> bool:
    """Проверить, разрешён ли переход заявки из old_status в new_status."""
    return new_status in ALLOWED_STATUS_TRANSITIONS.get(old_status, frozenset())