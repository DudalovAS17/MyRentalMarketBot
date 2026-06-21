from dataclasses import dataclass

from status.rental_status import RentalStatus

""" ! Доменные ошибки ! """

class DomainError(Exception):
    """Базовый класс доменных ошибок"""

""" ItemNotAvailable — это доменный сигнал “вещь занята” с полезными данными.
Роль — структурировано сообщить, ПОЧЕМУ операция невозможна (не описывает сущность БД и не DTO).
ItemNotAvailable — это НЕ ошибка исполнения, а ожидаемая бизнес-ситуация. 

@dataclass
    - автоматически создаёт __init__
    - хранит данные как у обычного объекта
    - делает код читаемым и явным
dataclass = удобная форма записи структуры данных.

Зачем это нужно именно здесь (смысл):
Когда пользователь пытается арендовать вещь, которая уже занята, нам нужно
    ❌ не просто сказать “нельзя”
    ✅ знать какая сделка мешает
    ✅ знать её статус
    ✅ знать до какого времени
Это доменное событие, а не просто return False.
"""
@dataclass
class ItemNotAvailable(DomainError): # Exception - чтобы корректно работало с raise / except
    item_id: int # какая вещь
    rental_id: int # Optional[int] # какая аренда блокирует
    status: RentalStatus # её статус
    #end_date: Optional[datetime]


@dataclass
class TicketAlreadyOpen(DomainError):
    ticket_id: int