# AGENT: Services

## Scope

Этот файл задаёт правила для слоя `services/` в проекте My-Rental-Bot.

Он нужен для любого агента, который:

- анализирует сервисы;
- предлагает новые service-классы;
- предлагает изменения существующих service-методов;
- делает review решений в business-layer;
- оценивает границы:
  - `handler ↔ service`
  - `service ↔ repository`
  - `service ↔ schema`
  - `service ↔ status`.

Этот файл не про весь проект, а только про слой сервисов.

---

## 1) Role of services

Service в этом проекте — это:

- слой бизнес-логики
- место принятия доменных решений
- место проверки бизнес-инвариантов
- место оркестрации нескольких репозиториев
- место реализации статусных переходов и policy-level checks
- граница `ORM/primitive from repo -> DTO/Pydantic наружу`

Service **не является**:

- Telegram-слоем
- FSM-слоем
- UI-слоем
- SQLAlchemy-слоем
- слоем прямого доступа к БД
- formatter-слоем
- местом для построения пользовательских сообщений
- местом для клавиатур и callback payload

Главный принцип:

> Service знает **что допустимо по правилам продукта**  
> и **как скоординировать доменную операцию**,  
> но не знает **как это показать пользователю**  
> и не знает **как писать SQL**.

Архитектурное ядро проекта фиксирует именно это:  
`Handlers → Services → Repositories → DB models`, и слой `Services` [отвечает за бизнес-правила и принятие решений](), 
без Telegram/FSM/UI и без прямых SQL-запросов. 

---

## 2) Hard boundaries

### Service layer may contain

Разрешено:

- простые типы (`int`, `str`, `bool`, `Decimal`, `datetime`)
- DTO/Pydantic-схемы (`Create`, `Update`, `Internal`, `Out`)
- вызовы одного или нескольких repositories
- orchestration нескольких repositories/services
- бизнес-проверки и инварианты
- проверки ролей, участников, ownership и policy
- проверки допустимости статусных переходов
- mapping ORM/primitive → DTO
- доменные исключения
- короткие логи бизнес-событий
- private helper methods для внутренней декомпозиции бизнес-логики

### Service layer must not contain

Запрещено:

- `Message`, `CallbackQuery`, `FSMContext`
- Telegram Bot API
- `InlineKeyboardMarkup`, клавиатуры, callback data
- user-facing тексты и UI-форматирование
- прямые SQLAlchemy-запросы
- `select`, `update`, `delete`, `session`, `commit`, `refresh`
- прямую работу с ORM как с внешним контрактом наружу
- возврат ORM в handlers/API
- логику маршрутизации и FSM
- транспортные детали

Архитектура проекта закрепляет это напрямую: сервисы принимают простые типы и DTO, координируют репозитории и 
проверяют бизнес-правила, но не работают с Telegram/FSM и не пишут SQL.

---

## 3) Service boundary relative to other layers

### Handler → Service

Handlers:

- получают пользовательский ввод
- делают минимальную UX/FSM-обработку
- вызывают service
- показывают результат пользователю

Service:

- не должен знать про Telegram-событие
- не должен знать про FSM
- не должен знать, какой текст/клавиатуру покажет handler

Архитектурно handlers “тонкие и тупые”, а service — слой правил.

### Service → Repository

Repository:

- читает/пишет БД
- знает ORM и SQLAlchemy
- не знает product-level смысла

Service:

- вызывает repo
- принимает решение, зачем и когда это делать
- не тянет SQLAlchemy-логику в себя
- не подменяет repo собственным persistence-layer

### Service → Schema

Service — это граница между внутренним слоем данных и внешним миром.

Правило:

- сервис принимает `Create/Update/Internal DTO` и простые типы
- репозиторий возвращает ORM/primitive
- сервис превращает это в `Out DTO`
- наружу из service-layer не выходит ORM

Это закреплено и в архитектуре, и в service-template: сервис работает через repo и
возвращает `*Out` через `model_validate(...)`.

---

## 4) Core contracts of the layer

## 4.1 Input contract

Service может принимать:

- primitive-аргументы
- `Create/Update` DTO
- `Internal` DTO
- actor IDs
- status enums
- pagination arguments
- domain-neutral flags вроде `strict`

Service не должен принимать:

- Telegram-объекты
- FSM-объекты
- raw UI payload
- ORM как обязательный внешний контракт
- SQLAlchemy session/query objects

### Canonical input style

Предпочтительно:

- write-операции: DTO + явные actor IDs + primitive-аргументы
- read-операции: primitive IDs + `strict=False/True`
- admin-операции: actor/admin IDs + domain arguments
- cross-entity операции: primitive args + один business payload

Service-template задаёт именно такой стиль: primitive/DTO input, `strict`, actor id как отдельный аргумент.

---

## 4.2 Output contract

### Предпочтительный канон

Public service methods должны возвращать:

- `XxxOut`
- `Optional[XxxOut]`
- `list[XxxOut]`
- `bool`
- `int`
- `tuple[...]`, если это уже устойчивый служебный контракт слоя
  (например `items + has_next`)

### Не возвращать наружу

Service **не должен** возвращать наружу:

- ORM
- SQLAlchemy objects
- user-facing text payload
- keyboard payload
- Telegram-specific objects

### Допустимые исключения

Разрешены специализированные контракты:

- `bool` для command-операций (`delete`, `close`, `move`, `set_order`)
- `tuple[list[DTO], has_next]` для пагинационных read-case’ов
- private helper внутри сервиса может временно работать с ORM,
  если это не public API сервиса

Из фактического слоя services видно, что `DTO + bool + tuple + Optional` уже реально используются 
как рабочий паттерн, но каноном для entity-boundary всё равно остаётся `Out DTO`.

---

## 5) Canonical service patterns

Ниже только те паттерны, которые уже подтверждены архитектурой и фактическим кодом сервисов.

### 5.1 Service как ORM → DTO boundary

Это сильный канон слоя:

- repo возвращает ORM
- service маппит в `*Out` через `model_validate(...)`
- handler получает DTO, а не ORM

Service-template закрепляет это прямо.

### 5.2 `strict`-контракт

Для типовых read/update/delete методов допустим устойчивый паттерн:

- `strict=False` → `None/False`
- `strict=True` → доменное исключение

Этот паттерн уже оформлен в template и повторяется по фактическому слою.

### 5.3 Service как policy engine

Status transitions, role checks, ownership checks, participant checks, domain gates — это место 
service-layer, а не handlers и не repositories. Это подтверждено и архитектурой, и фактическим анализом Codex.

### 5.4 Service как orchestration layer

Если use-case требует:

- нескольких repositories
- нескольких сущностей
- cross-entity инварианта
- post-write действий

это делает service.

### 5.5 Private helper pattern

Внутри сервиса допустимы private helper methods, если они:

- уменьшают дублирование
- держат бизнес-логику в одном месте
- не ломают внешний контракт сервиса

Например допустим паттерн “private transition helper + thin public methods”.

---

## 6) Service ↔ Repository boundary

### Правильное разделение

Repository отвечает на вопрос:

> как корректно прочитать/записать данные в БД?

Service отвечает на вопрос:

> можно ли это делать и каков доменный смысл операции?

### Service may do

Разрешено:

- вызвать один или несколько repo
- проверить результат repo
- принять business decision
- превратить ORM в DTO
- выполнить post-write orchestration
- повторно использовать repo-primitive results

### Service must not do

Запрещено:

- писать SQLAlchemy query logic
- делать `select`, `join`, `update`, `session`
- заниматься transaction semantics уровня repo
- принимать persistence-level решения вместо repo
- подменять repo в части DB mechanics

### Contract mismatch rule

Service обязан держать контракты `service ↔ repo` согласованными:

- по типу ID
- по названию ID
- по смыслу статусов
- по типам return values

Любой mismatch между service и repo — архитектурная ошибка.

---

## 7) Service ↔ Handler boundary

### Handler may do

- parse update/callback
- читать/писать FSM
- формировать текст
- формировать клавиатуры
- звать service
- показывать пользователю результат

### Service must not do

- принимать `Message`/`CallbackQuery`
- работать с `FSMContext`
- собирать клавиатуры
- формировать пользовательские тексты
- принимать UX-решения
- возвращать “готовый ответ для Telegram”

### Critical rule

Если handler сам решает:

- можно ли менять статус
- можно ли выполнять действие
- разрешён ли переход
- кто имеет право на действие

то это leakage бизнес-логики из service-layer.

---

## 8) Service ↔ Schema boundary

### Canon

Service должен:

- принимать `Create/Update/Internal` DTO
- возвращать `Out DTO`
- маппить ORM → DTO внутри себя
- не отдавать ORM наружу

### Draft/FSM data rule

Raw `dict` из FSM допустим только на уровне handlers.

Перед тем как выполнять бизнес-логику, service обязан привести такие данные к DTO/Pydantic. 
Это зафиксировано прямо в архитектуре.

### No DTO-out from repo

DTO boundary начинается в service-layer, а не в repo-layer.

---

## 9) Status and policy rules

### 9.1 Service owns policy

Status transition policy, role checks и domain invariants должны жить в service-layer.

### 9.2 Use status-layer enums

Сервисы должны использовать enum и helper functions из `status/`, а не импортировать статусные enum из `db.models.*`.

Это прямо вытекло из fact-based draft Codex: импорт статусов из ORM-моделей в сервисы — переходный компромисс, а не канон.

### 9.3 Repo may do atomic write, service decides legality

- repo может технически безопасно применить переход
- service решает, разрешён ли такой переход по бизнесу

### 9.4 Handlers must not own status policy

UX pre-check в handler допустим только как вспомогательный уровень, но источник истины по допустимости перехода — service.

---

## 10) ID conventions

Это жёсткое правило слоя.

Нужно явно различать:

- `user_id`, `owner_id`, `renter_id`, `reviewer_id`, `reviewee_id`, `admin_user_id` → DB ID
- `telegram_id`, `telegram_user_id`, `admin_tg_id`, `closed_by_admin_tg_id` → Telegram ID

### Rules

- не смешивать DB ID и Telegram ID в одной сигнатуре без явного названия
- conversion `telegram_id -> user_id` должен быть отдельным шагом/use-case
- избегать нейтральных имён вроде `admin_id`, если по смыслу это Telegram ID
- actor IDs в сигнатурах должны быть однозначными

Fact-based draft отдельно фиксирует, что naming ambiguity у ID — повторяющаяся слабость сервиса, 
и это нужно считать отдельным review-пунктом.

---

## 11) Time conventions

Во всём service-layer используется только aware UTC datetime.

Разрешено:

```python
from datetime import datetime, timezone
datetime.now(timezone.utc)
```

Запрещено:

- `datetime.now()` без timezone
- `datetime.utcnow()`
- local time в доменной логике
- timezone conversion
- человекочитаемое форматирование времени

Сервис:

- сравнивает aware UTC `datetime`
- проверяет time-based business rules
- не знает про локальное время пользователя

Архитектура проекта закрепляет это как единый закон времени.

---

## 12) Error handling conventions

### 12.1 Technical errors

Технические ошибки сервис не должен подавлять.

Они пробрасываются выше. Это закреплено в `service-template`.

### 12.2 Business errors

Service может и должен поднимать доменные ошибки, например:

- `not found`
- `conflict`
- `forbidden`
- `invalid transition`
- `duplicate action`
- `self-ban` / `self-action guard`

### 12.3 `strict` as business-facing contract

`strict` — допустимый инструмент для управления `not-found` поведением без дублирования сервисов.

### 12.4 Do not return UI-text as error contract

Сервис не должен формировать пользовательские тексты ошибок.

Он должен:

- возвращать structured result
- или бросать доменное исключение

---

## 13) Logging conventions

Service может логировать:

- факт бизнес-события
- краткий доменный контекст
- actor id
- id сущности

Service не должен:

- логировать stacktrace “на всякий случай” вместо верхнего технического слоя
- превращать логи в UI
- дублировать transport / error middleware

`service-template` прямо поддерживает короткие business-event логи после успешной операции.

---

## 14) Transport / notification exception

### Important exception

В фактическом коде есть `NotificationService`, который работает как Telegram transport adapter и содержит Telegram/UI-зависимости.

Fact-based draft явно фиксирует это как переходное исключение, а не канон business-layer.

### Canon rule

Transport / notification code:

- не считать каноном обычного service-layer
- не использовать как оправдание для Telegram leakage в новых сервисах
- по возможности трактовать как инфраструктурный adapter/service, а не business-service

---

## 15) Allowed specialized service contracts

Не все сервисы обязаны быть одинаковыми CRUD-wrapper’ами.

Допустимы:

### CRUD-like services

- `get_by_id`
- `list_*`
- `create`
- `update`
- `delete`

### Orchestration services

- несколько repo
- несколько сущностей
- cross-domain checks
- post-write actions

### Admin policy services

- административные override-операции
- audit trail
- role-aware decisions

### Domain-specific services

- ordering
- aggregate recalc
- workflow transition
- moderation checks

Но во всех случаях сохраняются границы слоя.

---

## 16) Comments inside services

Комментарии в сервисах допустимы, если они:

- объясняют нетривиальный business invariant
- объясняют статусный переход
- объясняют cross-repository orchestration
- фиксируют важный доменный компромисс

Не засорять сервисы:

- длинными историческими спорами
- UI-памятками
- “вставил без осознания”
- TODO-блоками без контрактного смысла
- транспортными деталями

Если комментарий не помогает понять бизнес-логику, он не должен жить в сервисе.

---

## 17) Transitional exceptions

Агент обязан различать:

- устойчивый канон service-layer
- исторические компромиссы
- локальные исключения
- прямые нарушения

Не поднимать автоматически до стандарта:

- Telegram-aware notification service внутри `services/`
- импорт статусных enum из `db.models.*`
- смешанные output-contracts как “идеальную норму”
- локальные naming-компромиссы
- раздвоение ответственности между двумя сервисами, если это исторический компромисс
- старые комментарии и design-notes внутри сервисов

Fact-based draft прямо предупреждает о таких переходных местах.

---

## 18) P0 / P1 / P2 for service review

### P0 — direct architectural violation

Критично:

- Telegram / FSM / UI inside service
- прямой SQLAlchemy / DB logic inside service
- возврат ORM наружу вместо DTO boundary
- business logic leakage в handlers
- import статусов из `db.models.*` вместо `status/`, если это склеивает service и ORM boundary
- смешение DB ID и Telegram ID в service contracts
- формирование пользовательских текстов в сервисе
- persistence-level решения вместо repo contracts

### P1 — architectural weakness / inconsistency

Не критично, но плохо:

- mixed input contracts без ясной политики
- mixed output contracts без ясной политики
- status logic partially duplicated
- service слишком thin и просто проксирует repo без business value
- service слишком fat и смешивает несколько разных ролей
- naming ambiguity: `admin_id`, `user_id`, `telegram_id`
- transport-like logic inside services как переходный компромисс
- unclear `strict` behavior
- слабая или неоднородная DTO mapping policy

### P2 — tech debt / cleanup

Не срочно:

- comments noise
- style inconsistency
- локальная типизационная полировка
- imports order
- docstring cleanup
- локальная декомпозиция private helpers без изменения контракта

Если есть P0, агент не должен уводить фокус на P2.

---

## 19) Review checklist for any service change

Перед тем как предложить новый сервис или изменение существующего, агент обязан проверить:

- Это действительно business-layer, а не Telegram/UI слой?
- Нет ли здесь `Message`, `CallbackQuery`, `FSMContext`?
- Нет ли здесь SQLAlchemy / query / session logic?
- Использует ли сервис repo как persistence API, а не подменяет его?
- Возвращает ли public service method DTO / primitive, а не ORM?
- Не утекла ли бизнес-логика в handler?
- Используются ли status enums из `status/`, а не из `db.models.*`?
- Ясно ли различены DB IDs и Telegram IDs?
- Нет ли format / text / keyboard leakage?
- Нужен ли здесь `strict`?
- Не должен ли вход быть DTO вместо набора сырых аргументов?
- Не должен ли выход быть DTO вместо mixed primitive / ORM?
- Есть ли здесь cross-repository orchestration, и находится ли оно в правильном месте?
- Не стал ли service временным транспортным адаптером под видом business-service?
- Не поднимается ли локальный компромисс до нового стандарта?

---

## 20) Output mode for the agent

Если агент анализирует `services/`, он должен отвечать так:

1. Что уже хорошо
2. Inventory services
3. Фактические architectural patterns
4. Transitional exceptions
5. P0 — прямые нарушения
6. P1 — архитектурные слабости
7. P2 — техдолг / cleanup
8. Candidate rules / final rules for service-layer
9. Open questions / ambiguities

Если агент предлагает изменение:

- не делать массовый рефактор
- предлагать один bounded-step
- учитывать, что пользователь может вносить изменения вручную
- не подменять анализ переписыванием всего слоя
- если нужен код — давать готовые фрагменты для ручной вставки

---

## 21) Final principle

Для слоя `services/` главный принцип такой:

> Service должен быть доменно сильным, архитектурно чистым и интерфейсно слепым.

Он:

- принимает решения по правилам продукта
- координирует доменные операции
- использует repo как слой данных
- отдаёт наружу только структурированный контракт
- не отдаёт ORM
- не отдаёт UI