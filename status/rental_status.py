import enum

class RentalStatus(enum.Enum):
    """Статус заявки клиента на аренду товара.

    Описывает путь заявки от отправки клиентом до обработки менеджером и финального закрытия."""

    REQUESTED = "requested"  # новая заявка от клиента; менеджер ещё не взял её в работу
    IN_PROGRESS = "in_progress" # заявка в обработке; менеджер уже смотрит наличие и связывается с клиентом
    CONFIRMED = "confirmed" # заявка подтверждена менеджером; условия согласованы, товар зарезервирован/готовится к выдаче
    REJECTED = "rejected" # заявка отклонена менеджером; например, товар недоступен или компания не может выполнить запрос
    COMPLETED = "completed" # заявка завершена; аренда отработана, товар возвращён/услуга закрыта
    CANCELLED_BY_CLIENT = "cancelled_by_client" # заявка отменена клиентом; клиент передумал или отказался от аренды
    CANCELLED_BY_ADMIN = "cancelled_by_admin" # заявка отменена менеджером/админом; например, клиент не отвечает, заявка дубль или условия не согласованы

    # ACTIVE = "active"
    # DISPUTED = "disputed"

# ───────────────────────────────────── классификация статусов ─────────────────────────────────────────────────────────
# после них заявка закрыта и дальше не должна двигаться.
TERMINAL_STATUSES: frozenset[RentalStatus] = frozenset({
    RentalStatus.REJECTED,
    RentalStatus.CANCELLED_BY_CLIENT,
    RentalStatus.CANCELLED_BY_ADMIN,
    RentalStatus.COMPLETED,
})

# Открытая заявка — это заявка, которая ещё влияет на доступность товара.
OPEN_STATUSES: frozenset[RentalStatus] = frozenset({
        RentalStatus.REQUESTED,
        RentalStatus.IN_PROGRESS,
        RentalStatus.CONFIRMED,
    })

# статус сам знает, какие поля времени нужно проставить при переходе.
STATUS_TIMESTAMP_FIELDS: dict[RentalStatus, tuple[str, ...]] = {
    RentalStatus.IN_PROGRESS: ("in_progress_at",),
    RentalStatus.CONFIRMED: ("confirmed_at",),
    RentalStatus.REJECTED: ("rejected_at", "closed_at"),
    RentalStatus.CANCELLED_BY_CLIENT: ("cancelled_at", "closed_at"),
    RentalStatus.CANCELLED_BY_ADMIN: ("cancelled_at", "closed_at"),
    RentalStatus.COMPLETED: ("completed_at", "closed_at"),
}

STATUS_LABELS: dict[RentalStatus, str]  = {
    RentalStatus.REQUESTED: "Заявка отправлена",
    RentalStatus.IN_PROGRESS: "В обработке",
    RentalStatus.CONFIRMED: "Подтверждена",
    RentalStatus.REJECTED: "Отклонена",
    RentalStatus.CANCELLED_BY_CLIENT: "Отменена клиентом",
    RentalStatus.CANCELLED_BY_ADMIN: "Отменена компанией",
    RentalStatus.COMPLETED: "Завершена",

    # RentalStatus.ACTIVE: "Активна",
    # RentalStatus.DISPUTED: "Спор открыт,
}

# ─────────────────────────────────────────── Переходы ─────────────────────────────────────────────────────────────────
ALLOWED_STATUS_TRANSITIONS: dict[RentalStatus, frozenset[RentalStatus]] = {
    RentalStatus.REQUESTED: frozenset({
        RentalStatus.IN_PROGRESS,
        RentalStatus.CONFIRMED,
        RentalStatus.REJECTED, # если менеджер ещё не подтвердил заявку, он её не “отменяет”, а отклоняет
        RentalStatus.CANCELLED_BY_CLIENT,
        #RentalStatus.CANCELLED_BY_ADMIN, # поэтому убираем это
    }),
    RentalStatus.IN_PROGRESS: frozenset({
        RentalStatus.CONFIRMED,
        RentalStatus.REJECTED, # пока заявка ещё в обработке, менеджер не отменяет подтверждённую услугу, а отклоняет заявку.
        RentalStatus.CANCELLED_BY_CLIENT,
        #RentalStatus.CANCELLED_BY_ADMIN, # поэтому убираем это
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

def status_timestamp_fields(status: RentalStatus) -> tuple[str, ...]:
    """Вернуть поля дат, которые нужно проставить при переводе заявки в статус."""
    return STATUS_TIMESTAMP_FIELDS.get(status, ())