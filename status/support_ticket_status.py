import enum

class SupportTicketStatus(enum.Enum):
    """Статус обращения клиента в поддержку."""

    OPEN = "open"      # обращение открыто и ждёт ответа/обработки менеджером
    CLOSED = "closed"  # обращение закрыто менеджером; вопрос решён или больше не требует действий


class SupportMessageSenderType(enum.Enum):
    """Отправитель сообщения внутри тикета поддержки."""

    USER = "user"
    ADMIN = "admin"
    SYSTEM = "system"