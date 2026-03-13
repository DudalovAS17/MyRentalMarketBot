# Template: Schemas (Pydantic / DTO)

## Правила:
- Create/Update/Out схемы
- Update применяется с exclude_unset=True
- ORM наружу не отдаём

## Законы схем
- Три схемы на сущность: XxxCreate, XxxUpdate, XxxOut
- DTO = контракт наружу, ORM наружу не отдаём
- XxxUpdate — только optional поля, применяется через exclude_unset=True
- XxxOut всегда содержит id + (если есть) created_at/updated_at
- XxxOut обязан уметь валидироваться из ORM: from_attributes=True

```
from typing import Optional
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ExampleBase(BaseModel):
    """Базовые поля сущности Example (общие для Create/Out)."""
    name: str # = Field(..., min_length=1)
    description: Optional[str] = None


class ExampleCreate(ExampleBase):
    """DTO для создания сущности.

    ЗАКОН:
    - Только то, что можно задать при создании извне.
    - Никаких системных полей (id, created_at, updated_at).
    """


class ExampleUpdate(BaseModel):
    """DTO для частичного обновления сущности.

    ЗАКОН:
    - Все поля Optional.
    - В repo применяется через model_dump(exclude_unset=True).
    """

    name: Optional[str] = None # = Field(None, min_length=1)
    description: Optional[str] = None


class ExampleOut(ExampleBase):
    """DTO для возврата данных наружу (handlers/API)."""

    id: int

    # В Pydantic v1 канон
    class Config:
        from_attributes = True
        
    # В Pydantic v2 канон
    model_config = ConfigDict(from_attributes=True)

```

---

## Наблюдения из текущих schemas (ориентиры)
- В `user/item/rental/review/support` используется полный набор Create/Update/Out — это основной канон.
- В `category` сейчас только `CategoryOut` (read-only кейс). Это допустимо, если сущность не создаётся через внешний ввод.
- `Photo` использует `Base`-схему и повторно применяет `from_attributes` в `Update` — это не обязательно, но допустимо.
- Валидация ограничений делается через `Field` (rating/price) и enum-статусы (`SupportTicketStatus`, `RentalStatus`).

---

✅ Про “Base-схему”: когда она нужна, а когда нет

Rule of thumb:
- Делай XxxBase, если реально есть “общие поля” для Create/Out
- Если сущность сложная и общих полей мало — можно без Base, это не преступление

✅ Про read-only сущности
- Если сущность не создаётся/не обновляется снаружи (например, только админ/seed),
  допускается оставить только XxxOut и зафиксировать это в файле (комментарий).