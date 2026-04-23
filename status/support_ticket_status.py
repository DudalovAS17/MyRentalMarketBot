import enum

class SupportTicketStatus(enum.Enum):
    """Статусы состояния тикета поддержки"""
    OPEN = "open"
    CLOSED = "closed"