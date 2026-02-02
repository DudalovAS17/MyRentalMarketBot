"""Item moderation statuses and transition rules."""

""" Что определяет видимость объявления:
- is_available → вторичный флаг, не источник истины
- пользовательский каталог никогда не ориентируется на is_available
- сервисы обязаны фильтровать по status

Пользователь:
    не влияет на модерацию
    не может «опубликовать» объявление сам
    

Новое объявление:
    - ВСЕГДА создаётся со статусом PENDING    
    - не видно в каталоге    
    - недоступно для аренды   
    - Даже если is_available=True — это игнорируется, пока статус не ACTIVE
    
    
PENDING / HIDDEN / REJECTED никогда не показываются

Перед созданием Deal:
    Item обязан быть ACTIVE
    Проверка делается:
    в сервисе
    независимо от UI
    Это дополняет (а не заменяет) ensure_item_available

владелец временно снял с аренды → is_available=False  


ACTIVE — объявление:
        видно в каталоге
        по нему можно начинать новые аренды
HIDDEN — объявление:
        снято с публикации
        новые сделки невозможны
        используется админом как “временно убрать с рынка”
"""

PENDING = "PENDING" # — ожидает модерации
ACTIVE = "ACTIVE" # — одобрено, видно в каталоге
HIDDEN = "HIDDEN" # — отклонено админом
REJECTED = "REJECTED" # — снято с публикации (админом)


ALLOWED_STATUS_TRANSITIONS = {
    PENDING: {ACTIVE, REJECTED},
    ACTIVE: {HIDDEN},
    HIDDEN: {ACTIVE},
    REJECTED: set(),
}

def can_transition(old_status: str, new_status: str) -> bool:
    """Return True if transition from old_status to new_status is allowed."""
    return new_status in ALLOWED_STATUS_TRANSITIONS.get(old_status, set())
