import enum

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

""" if new_status == "HIDDEN"
    Если не поставить guard, получится:
        - сделка продолжается
        - объявление скрыто
        - пользователь:
            не видит свой item в каталоге
            может потерять доступ к контексту сделки
        - админ:
            нарушил целостность модели “item ↔ deal”

    Почему НЕ проверяем другие статусы
    ❌ new_status == "ACTIVE"
        при активации объявления:                
            мы не ломаем сделки                
            наоборот, разрешаем рынок                
        нет риска консистентности                
    ❌ new_status == "REJECTED"                
        REJECTED применяется только из PENDING               
        по PENDING физически не может быть сделок                
        guard не нужен                
    ❌ new_status == "PENDING"                
        админ туда не переводит                
        пользовательских переходов тут нет
"""

class ItemStatus(enum.Enum): # это еще надо понять надо тут или нет, похожее уже где-то есть.
    ACTIVE = "ACTIVE" # "active" — одобрено, видно в каталоге
    PENDING = "PENDING" # "pending" — ожидает модерации
    REJECTED = "REJECTED" # "rejected" — снято с публикации (админом)
    HIDDEN = "HIDDEN" # "hidden" — отклонено админом

ALLOWED_STATUS_TRANSITIONS: dict[ItemStatus, set[ItemStatus]] = {
    ItemStatus.PENDING: {ItemStatus.ACTIVE, ItemStatus.REJECTED},
    ItemStatus.ACTIVE: {ItemStatus.HIDDEN},
    ItemStatus.HIDDEN: {ItemStatus.ACTIVE},
    ItemStatus.REJECTED: set(),
}

def can_transition(old_status: ItemStatus, new_status: ItemStatus) -> bool:
    """Return True if transition from old_status to new_status is allowed."""
    return new_status in ALLOWED_STATUS_TRANSITIONS.get(old_status, set())
