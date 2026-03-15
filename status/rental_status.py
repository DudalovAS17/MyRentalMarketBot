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

    #ADMIN_CANCELLED = "ADMIN_CANCELLED" - новый статус, реализуй

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
# Имеем ли мы право вмешиваться сейчас.
# Множество состояний, в которых сделка уже завершена по смыслу.


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


"""
Замечание: Нет whitelist-переходов (как в item_status.py). 
Переходы проверяются через _transition() в сервисе (по expected_status). 
Это работает, но при усложнении бизнес-логики стоит добавить ALLOWED_TRANSITIONS dict.
"""



# rental_ui хендлер
STATUS_LABELS = {
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










"""
Сделка всегда находится в одном статусе.
Переходы строго ограничены.

Никаких «если захотели — поменяли».

1. REQUESTED — «Запрос отправлен» (кто создает: арендатор - нажал «🤝 Арендовать»)

Что видит арендатор:
        Статус: ⏳ Ожидает подтверждения
        Кнопка: ❌ Отменить запрос

Что видит владелец:
        Новый запрос аренды
        Кнопки:
            ✅ Подтвердить
            ❌ Отклонить

Кто	   → Действие
OWNER  → CONFIRMED
OWNER  → REJECTED
RENTER → CANCELLED_BY_RENTER
-------------------------------------------

2. Переход: REQUESTED → CONFIRMED — «Подтверждено владельцем» (кто переводит: владелец)

Что видят оба:
        Даты аренды
        Контакт друг друга
        Статус: 🟢 Подтверждено
Кнопки:
    RENTER: ❌ Отменить (до начала)
    OWNER: ❌ Отменить (до начала)

Владелец согласился - Вещь «зарезервирована»
!Но что важно: Аренда еще не началась, это ожидание даты, т.е. перехода SYSTEM → ACTIVE
(начать аренду - сам бот автоматически)
-------------------------------------------

3. ACTIVE — «Аренда активна»
Переход: CONFIRMED → ACTIVE (Кто переводит: SYSTEM)
1) CONFIRMED: Владелец согласился (юридически/логически вы договорились)
2) ACTIVE: Фактическое пользование вещью началось (вещь передана, время пошло, депозит/оплата применились)

ACTIVE = “аренда идёт, вещь у арендатора, период считается, правила отмены/спора другие”

Чтобы ACTIVE означал реальный факт передачи, нам нужна “двухсторонняя фиксация”:
    владелец нажал «Передал вещь»
    арендатор нажал «Получил вещь»
    только когда оба события произошли → переводим в ACTIVE

В ACTIVE меняется всё:
    появляются основания для спора,
    отмена превращается в “разрыв активной аренды” (другие последствия),
    начинается (или считается) срок,
    можно “завершить” только после факта возврата.

Что видят оба:
    Статус: 🔵 Активна
    Дата окончания
Кнопки:
    🆘 Открыть спор (Сообщить о проблеме) 
    ❌ Досрочно завершить (опционально) - оба или только Владелец?

Переходы:
SYSTEM → COMPLETED (по end_date)
RENTER/OWNER → DISPUTED
-------------------------------------------

🟣 4. COMPLETED — «Завершена» (Кто переводит: SYSTEM \или\ OWNER подтвердил возврат)
Переход: ACTIVE → COMPLETED

Вещь возвращена
Финансы зафиксированы
Можно оставлять отзыв (👉 ТОЛЬКО здесь появляются отзывы)

Что видят оба:
    Статус: ✅ Завершена
    Кнопка: ⭐ Оставить отзыв (если не оставлен)
Переходы:
    нет (ФИНАЛ)
-------------------------------------------

🔴 5. REJECTED — «Отклонена» (кем: владельцем)
Переход: REQUESTED → REJECTED
Финал. Отзывов нет.

ЛИБО
⚫ 5.1. CANCELLED_BY_RENTER — «Отменено арендатором»
Переходы:
REQUESTED → CANCELLED_BY_RENTER
CONFIRMED → CANCELLED_BY_RENTER
ACTIVE → CANCELLED_BY_RENTER (опционально)

⚫ 5.2. CANCELLED_BY_OWNER — «Отменено владельцем»
Переходы:
REQUESTED → CANCELLED_BY_OWNER
CONFIRMED → CANCELLED_BY_OWNER
ACTIVE → CANCELLED_BY_OWNER (опционально)


⚠️ 8. DISPUTED — «Спор» (Кто: любой участник)
Когда: проблема во время ACTIVE

Что дальше:
    ручная обработка
    админ
    заморозка денег
"""