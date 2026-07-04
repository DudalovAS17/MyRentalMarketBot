
class ServiceError(Exception):
    """Базовая ошибка бизнес-слоя (services)."""


class NotFoundError(ServiceError):
    """Запрошенная сущность не найдена (строгий сценарий)."""


class ForbiddenError(ServiceError):
    """Действие запрещено бизнес-правилами."""


class ConflictError(ServiceError):
    """Действие конфликтует с текущим состоянием или инвариантами/статусами/занятость и т.п."""


class ValidationError(ServiceError):
    """Входные данные не прошли бизнес-валидацию."""


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
