# Template: Schemas (Pydantic / DTO)

## Правила:
- Create/Update/Out схемы
- Update применяется с exclude_unset=True
- ORM наружу не отдаём

```
from typing import Optional

from pydantic import BaseModel


class ExampleBase(BaseModel):
    name: str
    description: Optional[str] = None


class ExampleCreate(ExampleBase):
    """Схема для создания сущности."""


class ExampleUpdate(BaseModel):
    """Схема для частичного обновления сущности."""

    name: Optional[str] = None
    description: Optional[str] = None


class ExampleOut(ExampleBase):
    """Схема для отдачи данных наружу."""

    id: int

    class Config:
        from_attributes = True

```