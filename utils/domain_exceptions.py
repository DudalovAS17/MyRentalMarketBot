from dataclasses import dataclass
from typing import Literal

from status.item_status import ItemStatus

class DomainError(Exception):
    """Базовый класс доменных ошибок"""

ItemUnavailableReason = Literal["inactive", "out_of_stock", "unavailable",]

@dataclass(slots=True)
class ItemNotAvailable(DomainError):
    """Сигнализирует, что товар сейчас нельзя отправить в заявку аренды.

    MVP-логика:
    - товар не ACTIVE;
    - доступное количество равно 0;
    - товар недоступен по другой причине.

    Не связан с открытыми заявками/арендами.
    """

    item_id: int
    reason: ItemUnavailableReason = "unavailable"
    available_quantity: int | None = None
    item_status: ItemStatus | None = None

    def __str__(self) -> str:
        if self.reason == "inactive":
            return "Товар сейчас недоступен для аренды"

        if self.reason == "out_of_stock":
            return "Товара пока нет в наличии"

        return "Товар сейчас нельзя арендовать"

@dataclass
class TicketAlreadyOpen(DomainError):
    """Сигнализирует, что у пользователя уже есть открытый тикет поддержки."""
    ticket_id: int