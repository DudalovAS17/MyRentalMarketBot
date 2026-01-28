from __future__ import annotations

import enum
from typing import Any

"""
Если status — Enum (например: RentalStatus.CANCELLED_BY_OWNER). Тогда чаще всего в проекте 
статус хранится так:
    status — enum-объект,
    status.value — строка для БД/логики (например "cancelled_by_owner" или "CANCELLED_BY_OWNER")
"""

_TERMINAL_KEYWORDS = ("COMPLET", "REJECT", "CANCEL") # ("complet", "reject", "cancel")
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

def _normalize_status(status: Any) -> str:
    """ Обрабатывает
     - Enum
     - строку
    """
    if status is None: # статус отсутствует/непонятен
        return ""
    if isinstance(status, enum.Enum):
        # Тогда status — enum-объект, а status.value — строка для БД/логики ("cancelled_by_owner" или "CANCELLED_BY_OWNER")
        # Ее приводим к строке и в нижний регистр
        return str(status.value).lower() # .upper()

    # Потому что мы дальше ищем ключевые слова без учёта регистра. Это убирает массу мелких несовместимостей.

    # Если status — не Enum (строка/что угодно - например, "ACTIVE" или "active")
    return str(status).lower() # .upper()

def is_terminal_status(status: Any) -> bool:
    """Является ли статус терминальный (НЕ open)? True|False"""
    normalized = _normalize_status(status)
    if not normalized: # нету статуса! (fail-safe)
        return False  # open ✅

    # вернет True, если есть хоть одно совпадение с терминальным статусом
    return any(keyword in normalized for keyword in _TERMINAL_KEYWORDS)
"""
Оно последовательно проверяет:
    "complet" in "cancelled_by_owner" → False
    "reject" in "cancelled_by_owner" → False
    "cancel" in "cancelled_by_owner" → True

any() возвращает True, как только встречает первое True
"""

def is_open_status(status: Any) -> bool:
    """Является ли статус open (НЕ терминальный)"""
    normalized = _normalize_status(status)
    if not normalized:
        return True  # open ✅ (Тут уже True, так как "Является ли статус open - ДА!")

    # вернет True только, если ВСЕ статусы - open!
    return not is_terminal_status(normalized)
