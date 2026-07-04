# Template: Schemas (Pydantic / DTO)

Схемы в проекте — контракт между слоями. ORM наружу не отдаём: из service в handlers/API идут DTO.

Правила:
- Обычно на сущность есть `XxxCreate`, `XxxUpdate`, `XxxOut`.
- `XxxUpdate` — только optional поля; применяется через `model_dump(exclude_unset=True)`.
- `XxxOut` содержит `id` и системные поля (`created_at`, `updated_at`), если они есть в модели.
- Для ORM → DTO используем Pydantic v2: `model_config = ConfigDict(from_attributes=True)`.
- Валидацию ограничений держим в DTO (`Field`, enum-типы), а DB-level ограничения — в ORM.
- Для FSM-черновиков можно делать отдельные схемы вроде `ItemCreateDraft` с `extra="forbid"`.

---

### Каноничный шаблон

```python
from decimal import Decimal
from typing import Optional

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from status.item_status import ItemStatus


class ItemCreate(BaseModel):
    """Схема для создания товара каталога."""

    category_id: int
    subcategory_id: Optional[int] = None

    title: str = Field(..., min_length=3, max_length=200)
    description: Optional[str] = None
    short_description: Optional[str] = Field(None, max_length=300)

    price: Decimal = Field(..., ge=0)
    price_text: Optional[str] = Field(None, max_length=100)

    available_quantity: int = Field(1, ge=0)
    is_featured: bool = False
    sort_order: int = Field(0, ge=0)

    min_rental_period: int = Field(1, ge=1)
    max_rental_period: Optional[int] = Field(None, ge=1)


class ItemUpdate(BaseModel):
    """Схема для частичного обновления товара каталога."""

    category_id: Optional[int] = None
    subcategory_id: Optional[int] = None

    title: Optional[str] = Field(None, min_length=3, max_length=200)
    description: Optional[str] = None
    short_description: Optional[str] = Field(None, max_length=300)

    price: Optional[Decimal] = Field(None, ge=0)
    price_text: Optional[str] = Field(None, max_length=100)

    available_quantity: Optional[int] = Field(None, ge=0)
    is_featured: Optional[bool] = None
    sort_order: Optional[int] = Field(None, ge=0)

    min_rental_period: Optional[int] = Field(None, ge=1)
    max_rental_period: Optional[int] = Field(None, ge=1)


class ItemOut(BaseModel):
    """Схема для возврата данных товара каталога."""

    id: int
    category_id: int
    subcategory_id: Optional[int] = None

    title: str
    description: Optional[str] = None
    short_description: Optional[str] = None

    price: Decimal = Field(..., ge=0)
    price_text: Optional[str] = None

    available_quantity: int
    is_featured: bool
    sort_order: int

    min_rental_period: int
    max_rental_period: Optional[int] = None

    status: ItemStatus
    views_count: int
    orders_count: int

    created_at: AwareDatetime
    updated_at: AwareDatetime

    model_config = ConfigDict(from_attributes=True)
```

---

### Когда нужен `Base`-класс
- Делай `XxxBase`, если у `Create` и `Out` реально много общих полей.
- Если общих полей мало или DTO отличаются по смыслу — можно без `Base`, как сейчас сделано в `ItemCreate` / `ItemUpdate` / `ItemOut`.

### Read-only сущности
- Если сущность не создаётся из пользовательского ввода, допустимо оставить только `XxxOut`.
- Зафиксируй это комментарием в файле, чтобы не выглядело как недоделка.