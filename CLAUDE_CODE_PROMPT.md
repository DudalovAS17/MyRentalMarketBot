# CLAUDE CODE — ПОЛНЫЙ КОНТЕКСТ ПРОЕКТА MY-RENTAL-BOT

## РОЛЬ

Ты — Senior Python Backend Engineer / Tech Lead с глубокой экспертизой в aiogram 3, PostgreSQL/SQLAlchemy 2.0 async, Clean Architecture и Telegram-ботах коммерческого уровня. Ты работаешь над проектом My-Rental-Bot — Telegram-бот для аренды вещей (маркетплейс внутри Telegram).

## ПРОЕКТ

**Стек:** Python 3.11+, aiogram v3, SQLAlchemy 2.0 async, Alembic, PostgreSQL, Pydantic v2.
**Текущее состояние:** Работает регистрация, каталог категорий, создание объявлений, основной flow аренды. Alembic настроен и используется. PostgreSQL развёрнут. Redis и Docker пока нет.

## АРХИТЕКТУРА (строгие правила)

```
Handlers (UX/FSM/Router) → только UI, FSM, маршрутизация
        ↓
Services (бизнес-логика) → правила, инварианты, решения
        ↓
Repositories (DB access) → только SQLAlchemy, возвращают ORM
        ↓
ORM Models → только описание таблиц
```

**Контракты между слоями:**
- Handlers: принимают Message/CallbackQuery, вызывают сервисы, форматируют ответ. ЗАПРЕЩЕНО: SQLAlchemy, ORM-объекты, бизнес-логика.
- Services: принимают простые типы и DTO (Pydantic), возвращают DTO. ЗАПРЕЩЕНО: Telegram-объекты (Message, CallbackQuery, FSMContext, Bot), формирование UI.
- Repositories: принимают простые типы или DTO, возвращают ORM или примитивы. ЗАПРЕЩЕНО: бизнес-логика, Telegram.
- Schemas (Pydantic): XxxCreate, XxxUpdate, XxxOut. ORM наружу не отдаём.

**DI-механизм:** `ServicesMiddleware` кладёт сервисы в `data`, aiogram инжектит по имени параметра хендлера. `RegistrationCheckMiddleware` кладёт `data["user"]` как `UserOut` (DTO).

**Middleware chain (фиксированный порядок):**
1. `GlobalErrorMiddleware` — ловит технические ошибки, пробрасывает ServiceError
2. `ServicesMiddleware` — инжектит сервисы
3. `RegistrationCheckMiddleware` — проверяет регистрацию/блокировку, кладёт user
4. `AdminCheckMiddleware` — только на admin_router

**Ошибки:**
```
ServiceError (база)
├── NotFoundError
├── ForbiddenError
├── ConflictError
├── ValidationError
└── DomainError (структурированные доменные сигналы)
    ├── ItemNotAvailable
    └── TicketAlreadyOpen
```
- Repositories: пробрасывают исключения SQLAlchemy (не нормализуют)
- Services: выбрасывают только ServiceError и наследников
- Handlers: ловят только ServiceError → UX-ответ
- GlobalErrorMiddleware: ловит всё остальное → логирует stacktrace → нейтральный ответ

**Время:** Только `datetime.now(timezone.utc)`. Никаких `datetime.now()`, `datetime.utcnow()`, naive datetime. Форматирование и timezone-конверсия — только в helpers/formatters.

**Идентификаторы:** `db_user_id` (PK в БД) и `telegram_user_id` (Telegram ID) — НИКОГДА не путать. Все доменные FK (Item.user_id, Rental.owner_id, Rental.renter_id) — это db_user_id.

**Логирование:** Только lazy-format: `logger.info("text %s", var)`. ЗАПРЕЩЕНО: `logger.info(f"text {var}")`, `logger.info("text {}".format(var))`.

**Индексы в ORM:** Только через `__table_args__ = (Index(...),)`. Запрещено `index=True` в mapped_column.

---

## НАЙДЕННЫЕ БАГИ И ПРОБЛЕМЫ (приоритет исправления)

### КРИТИЧЕСКИЕ БАГИ (ломают функциональность)

**1. handlers/auth.py — несуществующие поля в UserCreate (строки 32-43):**
```python
# ❌ ТЕКУЩИЙ КОД — упадёт с Pydantic ValidationError
UserCreate(
    telegram_id=str(telegram_id),  # str вместо int
    ...
    rating=5.0,       # НЕТ в UserCreate
    rating_count=0,   # НЕТ в UserCreate
    is_blocked=False,  # НЕТ в UserCreate
)
```
ИСПРАВИТЬ: убрать rating, rating_count, is_blocked. Передавать `telegram_id=telegram_id` (int).

**2. services/review_service.py — logger.info с .format() стилем (строки ~последние):**
```python
# ❌ ТЕКУЩИЙ КОД — {} не интерполируются, в лог пойдёт буквально "{}"
logger.info(
    "Рейтинг пользователя {} обновлён: {} ({} отзывов)",
    user_id, avg_rating, count
)
```
ИСПРАВИТЬ: заменить `{}` на `%s`.

**3. utils/domain_exceptions.py — TicketAlreadyOpen наследует Exception:**
```python
# ❌ ТЕКУЩИЙ КОД
@dataclass
class TicketAlreadyOpen(Exception):  # ← не связан с ServiceError!
    ticket_id: int
```
GlobalErrorMiddleware пробрасывает ServiceError, а TicketAlreadyOpen — нет. Middleware залогирует его как "техническую ошибку".
ИСПРАВИТЬ: `class TicketAlreadyOpen(DomainError)`, и `class DomainError(ServiceError)` в utils/errors.py.

**4. handlers/rentals/flow_create.py — timezone сервера вместо UTC:**
```python
# ❌ ТЕКУЩИЙ КОД
tz = datetime.now().astimezone().tzinfo  # берёт TZ сервера!
start_dt = datetime.combine(start_date, time.min).replace(tzinfo=tz)
```
ИСПРАВИТЬ: `datetime.combine(start_date, time.min, tzinfo=timezone.utc)`

**5. handlers_rental_ui.py — кнопка "Оставить отзыв" не добавляется в rows (строки ~191, 229):**
```python
# ❌ ТЕКУЩИЙ КОД — создаётся объект, но НЕ добавляется в rows
elif status == RentalStatus.COMPLETED:
    InlineKeyboardButton(text="⭐ Оставить отзыв", callback_data=f"rental_action:review:{rental_id}")
```
ИСПРАВИТЬ: `rows.append([InlineKeyboardButton(...)])`.

**6. handlers_rental_ui.py строка 171 — неправильный username:**
```python
# ❌ renter_username вместо owner_username
f"👑 <b>Владелец:</b> {fmt_person(owner_name, renter_username)}\n\n"
```
ИСПРАВИТЬ: `fmt_person(owner_name, owner_username)`.

**7. services/rental_service.py — ensure_item_available передаёт str вместо Enum/datetime:**
```python
# ❌ ТЕКУЩИЙ КОД
raise ItemNotAvailable(
    status=open_rental.status.value,  # str, но dataclass ожидает RentalStatus
    end_date=open_rental.end_date.isoformat(),  # str, но ожидает Optional[datetime]
)
```
ИСПРАВИТЬ: убрать `.value` и `.isoformat()` — передавать enum и datetime напрямую.

**8. handlers/support.py — вызов SupportTicketCreate вместо SupportTicketCreateInternal:**

```python
# ❌ ТЕКУЩИЙ КОД — SupportTicketCreate НЕ имеет поля user_id
ticket = await support_service.create(ticket_data=)
```
ИСПРАВИТЬ: использовать `SupportTicketCreateInternal(user_id=user.id, ...)`.

### АРХИТЕКТУРНЫЕ ПРОБЛЕМЫ

**9. services/rental_service.py строки 394-596 — 200 строк мёртвого псевдокода:**
Закомментированный класс, псевдокод типа `confirm_rental(Владелец подтверждает):`. УДАЛИТЬ ПОЛНОСТЬЮ.

**10. services/item_service.py — дубликат admin_set_status() vs moderate_set_status():**
`admin_set_status` НЕ проверяет whitelist (TODO в коде). `moderate_set_status` проверяет.
УДАЛИТЬ `admin_set_status`, использовать только `moderate_set_status`.

**11. Schemas импортируют enum из ORM вместо из status/:**
```python
# ❌ В schemas/item.py, schemas/rental.py, schemas/support.py, schemas/user.py
from db.models.item import ItemStatus  # НЕПРАВИЛЬНО

# ✅ Правильно
from status.item_status import ItemStatus
```
ИСПРАВИТЬ во всех schemas/*.py.

**12. services/notif_service.py зависит от aiogram.Bot:**
Сервис не должен знать о Telegram. Это адаптер, не сервис. Пока не рефакторить, но зафиксировать как техдолг.

**13. services/rental_service.py — get_open_rental_for_item() возвращает ORM:**
Вызывается из хендлера (handlers/category.py:241), хендлер получает ORM-объект. Нарушение архитектуры.
ИСПРАВИТЬ: возвращать `Optional[RentalOut]` или None.

**14. db/repositories/review.py — не наследует BaseRepository:**
Единственный репозиторий, который дублирует логику вместо использования BaseRepository.
ИСПРАВИТЬ: наследовать от BaseRepository, использовать `_session()`, `_add_commit_refresh()`, etc.

**15. db/models/base.py — default вместо server_default для timestamps:**
```python
# ⚠️ Текущий код — время создаётся Python, не PostgreSQL
default=lambda: datetime.now(timezone.utc)
# ✅ Рекомендация — время создаётся на стороне БД
server_default=func.now()
```

**16. Handlers ловят технические ошибки вместо GlobalErrorMiddleware:**
В handlers/base.py, handlers/auth.py есть `except SQLAlchemyError`, `except Exception`. По архитектуре это должен делать middleware.

**17. f-string в логах:**
В handlers/auth.py (~15 мест), handlers/base.py (~5 мест), middlewares/registration_check.py (~5 мест).
ИСПРАВИТЬ: `logger.info(f"text {var}")` → `logger.info("text %s", var)`.

### МЕЛКИЕ ПРОБЛЕМЫ

**18. schemas/item.py — `min_rental_period: int = None`:**
`int` не может быть `None` по type hint. Должно быть `min_rental_period: int` (без default) или `Optional[int] = None`.

**19. db/repositories/user.py — `delete()` type hint `-> int` но возвращает `bool`.**

**20. db/models/user.py — дублирование is_blocked и account_status, is_admin хранится в БД но определяется конфигом.**

---

## СТАНДАРТЫ КОДА (применять при любых изменениях)

### Модели (ORM):
```python
from __future__ import annotations
from sqlalchemy import Integer, String, Index, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.models.base import Base, TimestampMixin

class Example(Base, TimestampMixin):
    __tablename__ = "examples"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    __table_args__ = (
        Index("ix_examples_name", "name"),
    )
```

### Репозитории:
```python
class ExampleRepository(BaseRepository):
    async def get_by_id(self, example_id: int) -> Optional[Example]:
        async with self._session() as s:
            return await s.get(Example, example_id)

    async def create(self, data: ExampleCreate) -> Example:
        async with self._session() as s:
            obj = Example(**data.model_dump())
            return await self._add_commit_refresh(s, obj)

    async def update(self, example_id: int, data: ExampleUpdate) -> Optional[Example]:
        async with self._session() as s:
            obj = await s.get(Example, example_id)
            if not obj:
                return None
            for k, v in data.model_dump(exclude_unset=True).items():
                setattr(obj, k, v)
            return await self._commit_refresh(s, obj)
```

### Сервисы:
```python
class ExampleService:
    def __init__(self, repo: ExampleRepository) -> None:
        self.repo = repo

    async def get_by_id(self, example_id: int, *, strict: bool = False) -> Optional[ExampleOut]:
        entity = await self.repo.get_by_id(example_id)
        if not entity:
            if strict:
                raise NotFoundError(f"Example not found: id={example_id}")
            return None
        return ExampleOut.model_validate(entity)

    async def create(self, payload: ExampleCreate) -> ExampleOut:
        obj = await self.repo.create(payload)
        logger.info("Example created id=%s", obj.id)
        return ExampleOut.model_validate(obj)
```

### Handlers:
```python
@router.callback_query(F.data.startswith("example:"))
async def handle_example(callback: CallbackQuery, example_service: ExampleService) -> None:
    await callback.answer()
    
    example_id = await parse_int_id_from_callback(callback)
    if example_id is None:
        return

    try:
        payload = await example_service.get_by_id(example_id, strict=True)
    except NotFoundError:
        await callback.answer("Не найдено", show_alert=True)
        return
    except ServiceError:
        await callback.answer("Ошибка при загрузке", show_alert=True)
        return

    await send_or_edit(callback, format_example_message(payload))
```

### Schemas:
```python
class ExampleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)

class ExampleUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)

class ExampleOut(BaseModel):
    id: int
    name: str
    created_at: AwareDatetime
    updated_at: AwareDatetime
    model_config = ConfigDict(from_attributes=True)
```

---

## ИНСТРУКЦИИ ДЛЯ РАБОТЫ

1. **Перед любым изменением** — прочитай соответствующий файл полностью через `cat` или `view`.
2. **Не ломай работающее** — каждое изменение должно сохранять текущую функциональность.
3. **Один коммит = одна логическая задача** — не мешай исправления багов с рефакторингом.
4. **Тестируй** — после каждого изменения запусти `python -c "from module import ..."` для проверки импортов.
5. **Комментарии на русском** — проект ведётся на русском. Код на английском.
6. **Не трогай Alembic миграции** без явного указания. Изменения моделей → новая миграция через `alembic revision --autogenerate`.
7. **Не создавай новых файлов** без явного указания — сначала исправляем существующие.

## ПОРЯДОК РАБОТЫ

Начинай с критических багов (пункты 1-8), затем архитектурные проблемы (9-17), затем мелочи (18-20). Для каждого исправления:
- Покажи что было (конкретные строки)
- Покажи что стало
- Объясни почему (одно предложение)

**Жди указания какой конкретно пункт исправлять. Не делай всё сразу.**
