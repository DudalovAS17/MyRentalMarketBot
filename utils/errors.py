
class ServiceError(Exception):
    """Базовая ошибка бизнес-слоя (services)."""


class NotFoundError(ServiceError):
    """Сущность не найдена (строгий сценарий)."""


class ForbiddenError(ServiceError):
    """Действие запрещено бизнес-правилами."""


class ConflictError(ServiceError):
    """Конфликт состояния (инварианты/статусы/занятость и т.п.)."""


class ValidationError(ServiceError):
    """Ошибка бизнес-валидации входных данных."""


# DomainError
# ValidationError (не путать с Pydantic)
