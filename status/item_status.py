import enum

class ItemStatus(enum.Enum):
    """ Статус товара в каталоге компании.

    Используется для управления жизненным циклом карточки товара:
    черновик → опубликован → временно скрыт / архивирован"""

    DRAFT = "draft" # товар создан, но ещё не опубликован
    ACTIVE = "active" # товар виден клиентам в каталоге
    HIDDEN = "hidden" # временно скрыт, но может быть возвращён
    ARCHIVED = "archived" # больше не используется, исторически сохранён


ALLOWED_STATUS_TRANSITIONS: dict[ItemStatus, frozenset[ItemStatus]] = {
    ItemStatus.DRAFT: frozenset({ItemStatus.ACTIVE, ItemStatus.HIDDEN, ItemStatus.ARCHIVED}),
    ItemStatus.ACTIVE: frozenset({ItemStatus.HIDDEN, ItemStatus.ARCHIVED}),
    ItemStatus.HIDDEN: frozenset({ItemStatus.ACTIVE, ItemStatus.ARCHIVED}),
    ItemStatus.ARCHIVED: frozenset(),
}

def can_transition(old_status: ItemStatus, new_status: ItemStatus) -> bool:
    """Проверить, разрешён ли переход товара из old_status в new_status"""
    return new_status in ALLOWED_STATUS_TRANSITIONS.get(old_status, frozenset())