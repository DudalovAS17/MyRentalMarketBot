from __future__ import annotations

import enum

class RentalActorRole(enum.Enum):
    OWNER = "owner"
    RENTER = "renter"

class RentalStatus(enum.Enum): # enum.StrEnum
    REQUESTED = "requested"      # Запрос отправлен арендатором
    CONFIRMED = "confirmed"      # Владелец подтвердил, ожидает начала аренды
    ACTIVE = "active"            # Аренда идет
    COMPLETED = "completed"      # Аренда завершена (вещь возвращена)

    REJECTED_BY_OWNER = "rejected_by_owner"    # Владелец отклонил запрос аренды
    REJECTED_BY_RENTER = "rejected_by_renter"  # Арендатор отклонил свой запрос аренды
    CANCELLED_CONFIRMED_BY_OWNER = "cancelled_confirmed_by_owner" # Владелец отменяет подтвержденную аренду
    CANCELLED_CONFIRMED_BY_RENTER = "cancelled_confirmed_by_renter" # Арендатор отменяет подтвержденную аренду
    CANCELLED_BY_OWNER = "cancelled_by_owner"  # Владелец отменяет активную аренду
    CANCELLED_BY_RENTER = "cancelled_by_renter" # Арендатор отменяет активную аренду

    DISPUTED = "disputed"        # Открыт спор

# "requested": "⏳ Запрошена",
# "confirmed": "✅ Подтверждена",
# "active": "▶️ Активна",
# "completed": "🏁 Завершена",
# "cancelled": "❌ Отменена",
# "rejected": "🚫 Отклонена",
# "disputed": "⚠️ Спор",
# "payment_pending": "💰 Ожидает оплаты",

""" Мы сознательно используем "complet", а не "complete", 
чтобы ловить и completed, и complete, и completion при необходимости.
("cancelled_by_owner" → содержит "cancel", "rejected_by_owner" → содержит "reject", "completed" → содержит "complet")


ТЕРМИНАЛЬНЫЙ СТАТУС = сделка завершена/ больше не “держит” вещь занятой / больше не должна блокировать аренду
ОСТАЛЬНОЕ — “open”.
Аренда открыта (сделка ещё “живёт”/ вещь занята) — БЛОКИРОВКА возможности создания новой аренды на тот же item.

терминальный ❌ / open ✅:
    REQUESTED = "requested"
    CONFIRMED = "confirmed"
    ACTIVE = "active"
    DISPUTED = "disputed"
    None (fail-safe)

терминальный ✅ / open ❌:
    COMPLETED = "completed" 
    REJECTED_BY_OWNER = "rejected_by_owner"
    REJECTED_BY_RENTER = "rejected_by_renter"
    CANCELLED_CONFIRMED_BY_OWNER = "cancelled_confirmed_by_owner"
    CANCELLED_CONFIRMED_BY_RENTER = "cancelled_confirmed_by_renter"
    CANCELLED_BY_OWNER = "cancelled_by_owner"
    CANCELLED_BY_RENTER = "cancelled_by_renter"
    
P.S. fail-safe = статус сломан/неизвестен (не позволяем создать вторую аренду)
Fail-safe может в редких случаях привести к “ложной занятости” (вещь не сдадут в аренду, хотя могла бы)
"""

# Терминальные статусы:
TERMINAL_STATUSES: frozenset[RentalStatus] = frozenset( # rozenset - Неизменяемый! Нельзя .add() / .remove()!
    {
        RentalStatus.COMPLETED,
        RentalStatus.REJECTED_BY_OWNER,
        RentalStatus.REJECTED_BY_RENTER,
        RentalStatus.CANCELLED_CONFIRMED_BY_OWNER,
        RentalStatus.CANCELLED_CONFIRMED_BY_RENTER,
        RentalStatus.CANCELLED_BY_OWNER,
        RentalStatus.CANCELLED_BY_RENTER,
    }
)

# Open статусы:
OPEN_STATUSES: frozenset[RentalStatus] = frozenset(
    {
        RentalStatus.REQUESTED,
        RentalStatus.CONFIRMED,
        RentalStatus.ACTIVE,
        RentalStatus.DISPUTED,
    }
)

def is_terminal_status(status: RentalStatus) -> bool:
    """True если статус терминальный (сделка завершена)."""
    return status in TERMINAL_STATUSES # находится ли переданный статус в наборе терминальных статусов.

def is_open_status(status: RentalStatus) -> bool:
    """True если статус open (сделка активна/жива и блокирует вещь)."""
    return status in OPEN_STATUSES

def open_statuses() -> tuple[RentalStatus, ...]:
    """Стабильный список open-статусов (удобно для .in_(...))."""
    return tuple(OPEN_STATUSES)
# Rental.status.in_(open_statuses())