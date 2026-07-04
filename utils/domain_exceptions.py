from dataclasses import dataclass

from status.rental_status import RentalStatus

class DomainError(Exception):
    """Базовый класс доменных ошибок"""

"""ItemNotAvailable — это доменный сигнал “вещь занята” с полезными данными.
Роль — структурировано сообщить, ПОЧЕМУ операция невозможна (не описывает сущность БД и не DTO).
ItemNotAvailable — это НЕ ошибка исполнения, а ожидаемая бизнес-ситуация."""
@dataclass
class ItemNotAvailable(DomainError):
    """Сигнализирует, что товар заблокирован активной арендой."""
    item_id: int # какая вещь
    rental_id: int # какая аренда блокирует
    status: RentalStatus # её статус

@dataclass
class TicketAlreadyOpen(DomainError):
    """Сигнализирует, что у пользователя уже есть открытый тикет поддержки."""
    ticket_id: int