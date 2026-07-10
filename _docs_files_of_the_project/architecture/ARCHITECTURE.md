# Архитектура проекта MyRentalMarketBot

Статус файла: актуализирован как обзорная карта архитектуры. Детальные правила вынесены в каноничные документы `_docs_files_of_the_project/agents/` и `_docs_files_of_the_project/architecture/`.

Цель документа — быстро показать, какие слои есть в проекте, кто за что отвечает и куда смотреть за подробными правилами перед рефакторингом или добавлением нового кода.

---

## 1) Главный принцип

Проект строится слоями:

```text
Telegram / aiogram event
    ↓
handlers/              UX, FSM, callback/message flow
    ↓
services/              business rules, invariants, status policy
    ↓
db/repositories/       SQLAlchemy queries and persistence
    ↓
db/models/             ORM mapping to database tables
```

Обратные зависимости запрещены: repository не знает про service/handler, service не знает про Telegram UI, handler не знает про SQLAlchemy.

---

## 2) Ответственность слоёв

### `handlers/` — UX / FSM / Router

Handler знает, что показать пользователю и как вести сценарий.

Разрешено:

- `Message`, `CallbackQuery`, `FSMContext`;
- router decorators и aiogram filters;
- callback/text parsing и простые UX-guards;
- вызов service через DI;
- обработка ожидаемых `ServiceError` / domain errors для понятного UX;
- сборка короткого текста или вызов formatter/helper.

Запрещено:

- SQLAlchemy, `select`, `session`, ORM-запросы;
- прямые вызовы repositories;
- business-policy и статусные переходы как источник истины;
- broad `except Exception` как обычный путь.

Подробно: `_docs_files_of_the_project/agents/handlers.md`.

### `services/` — business layer

Service знает, что допустимо по правилам продукта.

Разрешено:

- вызывать repositories и другие services;
- проверять ownership, статусы, конфликты, инварианты;
- маппить ORM → DTO через `model_validate()`;
- поднимать `ServiceError`-наследников и domain errors;
- писать короткие business/audit logs без PII.

Запрещено:

- Telegram/FSM/UI objects;
- SQLAlchemy query/session/commit;
- возврат ORM наружу;
- форматирование пользовательского UI.

Подробно: `_docs_files_of_the_project/agents/service.md`.

### `db/repositories/` — persistence/query layer

Repository знает, как читать и писать данные.

Разрешено:

- SQLAlchemy queries;
- ORM models из `db.models.*`;
- `AsyncSession` через `BaseRepository._session()`;
- commit/rollback/refresh через helpers `BaseRepository`;
- возврат ORM / `list[ORM]` / primitive.

Запрещено:

- Telegram/FSM/UI;
- DTO как output-контракт;
- user-facing тексты;
- business-policy как источник истины;
- скрытое подавление DB-ошибок.

Подробно: `_docs_files_of_the_project/agents/repositories.md`.

### `db/models/` — ORM

Models описывают таблицы, relationships и DB-level defaults.

Правила:

- модели не содержат Telegram/UI-логики;
- бизнес-переходы не реализуются в ORM как основной механизм;
- datetime-поля должны быть timezone-aware;
- связи загружаются явно/eager там, где это нужно service после закрытия session.

Подробно: `_docs_files_of_the_project/agents/model.md`.

### `schemas/` — DTO boundary

Schemas описывают входные и выходные контракты.

Правила:

- `Create` — поля, которые можно задать при создании;
- `Update` — partial update, все изменяемые поля optional;
- `Out` — безопасный output из service в handlers;
- `Out`, построенный из ORM, должен иметь `ConfigDict(from_attributes=True)`;
- DTO не проверяет существование сущностей в БД и не решает permissions/business-policy.

Подробно: `_docs_files_of_the_project/agents/schemas.md` и `_docs_files_of_the_project/architecture/orm_dto_boundaries.md`.

### `middlewares/` — глобальные политики приложения

Middleware отвечает за cross-cutting concerns:

- прокидывание services/user/admin в handler data;
- registration/admin checks;
- централизованную обработку неожиданных технических ошибок.

Middleware не должен становиться местом продуктовой бизнес-логики конкретного сценария.

Подробно по ошибкам: `_docs_files_of_the_project/architecture/error_handling.md`.

---

## 3) Ошибки и logging

Канон:

- handler ловит ожидаемые `ServiceError` / domain errors, если нужно показать конкретный UX-текст;
- технические `Exception` не ловятся в каждом handler-е;
- `GlobalErrorMiddleware` логирует unexpected traceback и показывает нейтральный текст пользователю;
- service поднимает business errors и не подавляет DB/network errors;
- repository не пишет user-facing сообщения и не превращает неизвестные DB-ошибки в UX.

Rollback сейчас остаётся в `BaseRepository._commit_or_rollback()` как централизованный safety-net для write-методов, пока в проекте нет Unit of Work / transaction middleware. Rollback делается только вокруг `commit()`, не вокруг всего метода.

Подробно: `_docs_files_of_the_project/architecture/error_handling.md`.

---

## 4) ORM ↔ DTO boundary

Канон:

```text
repository returns ORM/primitive
service maps ORM → DTO
handler receives DTO/primitive
```

Repository может принимать `Create`/`Update` DTO как вход для записи, но не должен возвращать DTO. Handler не должен использовать ORM как рабочий контракт и не должен класть ORM в FSM/keyboards/formatters.

Подробно: `_docs_files_of_the_project/architecture/orm_dto_boundaries.md`.

---

## 5) Startup / composition root

Запуск приложения собирается вокруг `main.py` и `app/*`:

```text
main.py
    ↓
config.py reads settings
    ↓
db/bootstrap.py checks/init DB
    ↓
app/routers.py registers routers
    ↓
app/container.py builds repositories/services
    ↓
app/middlewares_setup.py registers middlewares
    ↓
aiogram polling
```

Ответственность файлов:

- `config.py` — typed settings из ENV/.env;
- `main.py` — lifecycle приложения;
- `app/container.py` — сборка repositories/services;
- `app/routers.py` — подключение routers;
- `app/middlewares_setup.py` — подключение middlewares;
- `db/bootstrap.py` — bootstrap/проверка БД.

Подробно: `_docs_files_of_the_project/architecture/main.md`, `_docs_files_of_the_project/architecture/config.md`, `_docs_files_of_the_project/architecture/_.md`.

---

## 6) Время в проекте

Единый стандарт: в домене и БД используется только timezone-aware `datetime` в UTC.

Разрешено:

```python
from datetime import datetime, timezone

now = datetime.now(timezone.utc)
```

Запрещено:

- `datetime.now()` без timezone;
- `datetime.utcnow()`;
- хранение naive datetime;
- сравнение naive и aware datetime;
- локальное время в БД;
- timezone conversion внутри ORM/services.

По слоям:

- ORM/DB: `DateTime(timezone=True)` и UTC;
- services: сравнения и бизнес-расчёты только с aware UTC datetime;
- schemas: в `Out` использовать `AwareDatetime`, если поле обязано быть aware;
- UI/helpers/formatters: единственное место, где допустимо человекочитаемое форматирование и локализация timezone.

Локальное время — это задача отображения, не доменной логики.

---

## 7) `from __future__ import annotations`

Правило:

- допустимо в ORM-моделях и Pydantic-схемах, если это реально упрощает forward references/type hints;
- в handlers, services, repositories и middleware не добавлять без явной необходимости.

---

## 8) Шаблоны и агентские правила

Каноничные агентские правила лежат в `_docs_files_of_the_project/agents/`:

- `handlers.md`;
- `service.md`;
- `repositories.md`;
- `schemas.md`;
- `model.md`;
- `status.md`.

Шаблоны лежат в `_docs_files_of_the_project/templates/`:

- `handler_template.md`;
- `service_template.md`;
- `repository_template.md`;
- `schema_template.md`;
- `model_template.md`;
- `middleware_template.md`.

Новый модуль должен соответствовать своему агентскому документу и использовать шаблон как стартовую структуру, если создаётся с нуля.

---

## 9) Архитектурный чеклист

- [ ] Handler не импортирует SQLAlchemy и repositories.
- [ ] Service не импортирует Telegram/FSM/UI и не возвращает ORM.
- [ ] Repository не возвращает DTO и не содержит business-policy/user-facing тексты.
- [ ] ORM не протекает в handlers/FSM/keyboards/formatters.
- [ ] `Create`/`Update`/`Out` DTO соответствуют правилам schemas.
- [ ] Business errors представлены `ServiceError`-наследниками или domain errors.
- [ ] Технические ошибки централизованно обрабатывает `GlobalErrorMiddleware`.
- [ ] Write repository methods используют commit helpers.
- [ ] Время в домене/БД — aware UTC.
- [ ] Новые статусные переходы описываются в `status/*` и проверяются в service.
