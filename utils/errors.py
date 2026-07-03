
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


"""Рекомендованное правило для проекта

1) ServiceError (ожидаемая ошибка)
пользователю: коротко
лог: logger.warning(...) (обычно без exc_info=True)

2) Любая “неожиданная” ошибка (Exception)
не ловим в хендлере
глобальный error middleware логирует stacktrace и показывает общий текст пользователю
"""
