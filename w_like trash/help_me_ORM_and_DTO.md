# ORM и DTO в проекте My-Rental-Bot

Этот документ фиксирует ключевое архитектурное различие между ORM и DTO
и правила их использования в проекте.

Цель — предотвратить утечки SQLAlchemy-логики наружу,
обеспечить единый стиль слоёв и упростить поддержку кода.

---

## 1) ORM — что это в данном проекте

**ORM (Object-Relational Mapping)** — это SQLAlchemy-модели,
которые напрямую связаны с базой данных.

В проекте ORM находятся в директории:

db/models/

### Пример ORM-модели

```python
class Item(Base):
    __tablename__ = "items"

    id = mapped_column(Integer, primary_key=True)
    user_id = mapped_column(Integer, nullable=False)
    title = mapped_column(String)
    price = mapped_column(Integer)
    status = mapped_column(String, default="PENDING")
```

### Свойства ORM
- напрямую связан с БД
- живёт внутри SQLAlchemy-сессии
- может иметь lazy relationships
- требует commit / rollback
- мутируем
- опасен за пределами слоя БД

**Правило:** ORM не должен использоваться в handlers.

---

## 2) DTO — что это в данном проекте

**DTO (Data Transfer Object)** — это Pydantic-схемы,
используемые для передачи данных между слоями
и наружу (handlers, форматирование, UI).

В проекте DTO находятся в директории:

schemas/

### Пример DTO

```python
class ItemOut(BaseModel):
    id: int
    user_id: int
    title: str
    price: int
    status: str
```

### Свойства DTO
- не связан с БД
- не имеет сессии
- безопасен для передачи
- сериализуем
- используется в handlers и utils

---

## 3) Где что используется (жёсткое правило)

| Слой | Тип данных |
|-----|-----------|
| db/models | ORM |
| db/repositories | ORM |
| services | ORM → DTO |
| handlers | DTO |
| keyboards / utils / formatters | DTO |

---

## 4) Поток данных (реальный пример)

### Репозиторий (ORM)

```python
async def get_by_id(self, item_id: int) -> Optional[Item]:
    async with self._sf() as s:
        return await s.get(Item, item_id)
```

Репозиторий возвращает **ORM-объект**.

### Сервис (граница ORM → DTO)

```python
async def get_item_by_id(self, item_id: int) -> Optional[ItemOut]:
    obj = await self.item_repo.get_by_id(item_id)
    if not obj:
        return None
    return ItemOut.model_validate(obj)
```

### Handler (только DTO)

```python
@router.callback_query(...)
async def item_view(callback: CallbackQuery, item_service: ItemService):
    item = await item_service.get_item_by_id(item_id)
    await callback.message.answer(item.title)
```

---

## 5) ItemCreate / ItemUpdate — тоже DTO

DTO бывают:
- выходные (ItemOut)
- входные (ItemCreate, ItemUpdate)

```python
class ItemCreate(BaseModel):
    title: str
    price: int
```

**Правило:**
- DTO может передаваться в репозиторий
- DTO никогда не возвращается из репозитория

---

## 6) Почему нельзя отдавать ORM наружу

Если ORM попадает в handlers:
- возможны lazy-загрузки в неожиданный момент
- утечки SQLAlchemy-сессий
- сложные баги при FSM
- проблемы при рефакторинге
- неявные side-effects

DTO устраняет эти риски.

---

## 7) Короткая формула проекта

ORM живёт только в репозиториях и сервисах.
DTO — единственный формат данных, который выходит из сервисов наружу.

---

## 8) Статус документа

Документ является частью архитектурного ядра проекта.
Обязателен к соблюдению при рефакторинге, добавлении новых модулей
и генерации кода (включая AI-инструменты).
