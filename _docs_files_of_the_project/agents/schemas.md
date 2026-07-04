# AGENT: Schemas

Файл задаёт правила для слоя `schemas/` в `MyRentalMarketBot`.

Нужен агентам, которые:
- анализируют Pydantic DTO;
- добавляют или правят `Create` / `Update` / `Out` схемы;
- ревьюят контракты между handlers, services и repositories;
- отделяют ORM от внешнего контракта.

Главный принцип:

> Schema определяет, **какие данные можно принять или вернуть**, но не решает, **что бизнес-разрешено делать**.

---

## 1) Scope слоя

`schemas/` — DTO/validation boundary.

Разрешено:
- `BaseModel`, `Field`, `ConfigDict(from_attributes=True)`;
- `AwareDatetime` для aware timestamps в `Out`;
- `Decimal` для денег и точных чисел;
- enum-типы проекта (`ItemStatus`, `RentalStatus`, ...);
- validators формы данных;
- `Create`, `Update`, `Out`, `AdminOut`, `Draft`, `Internal` DTO.

Запрещено:
- SQLAlchemy и ORM-запросы;
- Telegram/FSM/UI объекты;
- user-facing тексты;
- DB existence checks;
- permission/business-policy checks;
- side effects.

---

## 2) Каноничные типы схем

`XxxCreate`:
- вход для создания;
- только поля, которые можно задать извне;
- без `id`, `created_at`, `updated_at`, audit-полей, если их задаёт service/DB.

`XxxUpdate`:
- partial update;
- все изменяемые поля optional;
- repository применяет через `model_dump(exclude_unset=True)`.

`XxxOut`:
- output из service в handlers/API;
- содержит `id` и нужные read-поля;
- содержит timestamps, если они есть в домене;
- обязан иметь `model_config = ConfigDict(from_attributes=True)`.

`XxxCreateDraft` / `XxxUpdateDraft`:
- временный FSM contract;
- почти всё optional;
- не подменяет финальный `Create` / `Update`;
- желательно `model_config = ConfigDict(extra="forbid")`.

`XxxAdminOut` / `XxxAdminUpdate`:
- отдельный контракт для админки, если админ видит/меняет больше полей.

---

## 3) Пример схем

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
    price: Decimal
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

## 4) Валидация

В schemas допустимо:
- длина строк;
- min/max чисел;
- required/optional структура;
- enum type;
- форма телефона/текста, если это именно форма данных.

В schemas запрещено:
- проверять, существует ли category/item/user в БД;
- решать, можно ли перейти из статуса в статус;
- проверять права админа/пользователя;
- считать стоимость аренды, если это business rule.

---

## 5) Time, Decimal, IDs

Time:
- в `Out` использовать `AwareDatetime` для aware UTC дат из БД;
- не превращать datetime в строку на уровне schema.

Decimal:
- цены, суммы, залоги — `Decimal`, не `float`.

IDs:
- `id`, `user_id`, `item_id`, `rental_id` — DB PK/FK;
- `telegram_id`, `*_tg_id` — внешний Telegram ID;
- имя поля должно явно показывать тип идентификатора.

---

## 6) Checklist

- [ ] `Out` имеет `ConfigDict(from_attributes=True)`.
- [ ] `Update` состоит из optional изменяемых полей.
- [ ] `Create` не содержит системные поля.
- [ ] Нет SQLAlchemy/Telegram/FSM imports.
- [ ] Деньги представлены через `Decimal`.
- [ ] Временные поля в `Out` — `AwareDatetime`.
- [ ] Admin/Draft/Internal контракты отделены от обычных пользовательских DTO.
