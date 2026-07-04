# AGENT: Handlers

Этот файл задаёт правила для слоя `handlers/` в проекте `My-Rental-Bot`

Он нужен для любого агента, который:

- анализирует хендлеры
- предлагает новые handler-функции
- предлагает правки существующих handler-flow
- делает review границ:
  - `handler ↔ service`
  - `handler ↔ FSM`
  - `handler ↔ formatter / keyboard`
  - `handler ↔ middleware`

```
Handlers: взаимодействие с пользователем и управление пользовательским сценарием.
Handlers: отвечают только за интерфейс, но не за логику приложения.
Handlers: не знают почему что-то происходит, они знают только что показать.
```

Этот файл не про весь проект, а только про слой `handlers/`

---

## 1) Role of handlers

`Handler` в этом проекте — это
- UX / FSM / router-слой
- точка входа пользовательского действия
- слой маршрутизации `update/callback`
- слой минимальной обработки входа
- слой, который вызывает сервис и показывает результат пользователю

`Handler` **не является**:

- слоем бизнес-логики
- слоем SQLAlchemy / DB
- слоем ORM
- местом доменных решений
- местом статусных переходов
- местом проверки бизнес-инвариантов

[**Главный принцип:**]()

> **`Handler` знает [что показать пользователю]() и [как провести его по сценарию](), 
> но [не знает почему доменно это допустимо]() и [не знает как устроена БД]()**.

Архитектура проекта прямо фиксирует, что `handlers` отвечают только за UX, FSM и маршрутизацию, 
могут работать с `Message`, `CallbackQuery`, `FSMContext`, разбирать вход, формировать текст/клавиатуры 
и вызывать сервисы, но не должны делать SQLAlchemy-запросы, работать с ORM и принимать доменные решения.

---

## 2) Hard boundaries

### Handler layer may contain

Разрешено:

- `Message`, `CallbackQuery`
- `FSMContext` (установка / чтение / очистка состояний / хранение промежуточных данных сценария)
- router decorators и фильтры
- разбор входных данных (update/callback) - parsing
- callback parsing
- `state.set_state`, `state.update_data`, `state.get_data`, `state.clear`
- text/keyboard rendering (формирование текста/клавиатуры)
- вызовы сервисов
- вызовы formatter/helper/keyboard builder
- короткие UX-guards
- обработку **бизнес-ошибок** сервисов
- `send_or_edit`, `callback.answer`, `message.answer`, `edit_text` и другие UX-ответы

### Handler layer must not contain

Запрещено:

- прямые repository вызовы
- SQLAlchemy queries (прямые SQLAlchemy-запросы)
- ORM-модели в качестве рабочего контракта
- доменные решения
- статусные переходы, реализованные вручную в handler
- permission matrix уровня бизнеса
- ownership/business-policy checks как источник истины
- raw FSM dict как бизнес-контракт сервиса
- обработку технических ошибок broad `except Exception` как стандартный путь
- импорт DB models / enum из ORM-слоя

Архитектура и шаблон `handler’а` закрепляют это жёстко: `handler` — только UX/FSM/router, минимум логики, 
никаких ORM/SQLAlchemy и никаких доменных решений.

---

## 3) Handler boundary relative to other layers

### [Handler → Service]()

Канон:

- `handler` получает вход
- делает минимальную UX-обработку
- вызывает `service`
- получает DTO / primitive result
- форматирует ответ
- отвечает пользователю

`Handler` не должен:

- сам решать, допустимо ли действие
- сам вычислять доменную политику
- подменять сервис собственной бизнес-логикой

### [Handler → FSM]()

FSM нужен только как:

- временное хранилище сценария
- draft-данные UX-потока
- выбранные id, page, mode, ui-message-id и т.п

`FSM не является бизнес-контрактом сервиса`

### [Handler → Formatter / Keyboard]()

`Handler` может:

- выбирать `formatter`
- вызывать `keyboard builder`
- собирать короткие локальные тексты
- вызывать `send_or_edit`

Но крупные тексты и сложные клавиатуры по мере роста должны выноситься в `helpers/formatters`.

Архитектура прямо фиксирует, что raw `dict` из FSM допустим только на уровне `handlers` и 
перед бизнес-логикой должен приводиться к `DTO/Pydantic`.

---

## 4) Core contracts of the layer

## 4.1 Input contract

`Handler` может принимать:

- `message: Message`
- `callback: CallbackQuery`
- `state: FSMContext`
- injected `services`
- `middleware-provided objects` (`user`, `admin_ids`, и т.п.)
- `callback/raw input values` после UX-parsing.

`Handler` не должен принимать как рабочий контракт:

- ORM-модели
- `repositories`
- SQLAlchemy session/query objects
- raw DB enums из `db.models.*`

---

## 4.2 Output contract

`Handler` может выдавать:

- `message.answer(...)`
- `callback.answer(...)`
- `callback.message.edit_text(...)`
- `send_or_edit(...)`
- state transitions / clear / update_data
- formatter + keyboard output

`Handler` не должен выдавать наружу как “результат своей логики”:

- ORM
- repository primitives как substitute UI
- raw DB objects
- доменные решения вместо UX-ответа

---

## 5) Canonical handler patterns

Ниже только паттерны, которые уже подтверждены архитектурой, шаблоном и фактическим анализом текущих `handlers`.

### 5.1 Handler как UX entry-point

Повторяющийся сильный паттерн:

- принять `event`
- получить нужный `service`
- минимально разобрать вход
- вызвать `service`
- отдать пользователю UX-ответ

### 5.2 Parse input → service → formatter / keyboard → answer

Это основной канон handler-flow.

### 5.3 Callback handler pattern

Типовой `callback-handler`:

1. `await callback.answer()`
2. `parse callback payload` / `id`
3. `invalid input` → короткий UX-guard
4. `service` call
5. render `text` / `keyboard`
6. `send_or_edit(...)` или `edit_text(...)`

### 5.4 FSM collect → DTO → service

Для `create/edit-flow` канон такой:

- `handler`/FSM собирает временные поля
- raw dict остаётся только на UX-уровне
- перед `service` call данные переводятся в `Draft` / `Create` / `Update` DTO

Это прямо согласуется и с архитектурой, и с шаблоном.

### 5.5 None-guard в handler

Если сервис при `strict=False` вернул `None`, это normal UX-branch:
- `handler` показывает пользователю понятный ответ
- не трактует это как техошибку

Шаблон `handler’а` отдельно фиксирует это как handler responsibility.

### 5.6 Business exception → короткий UX ответ

`Handler` может локально ловить:
- `ServiceError`
- `NotFoundError`
- domain exceptions вроде `TicketAlreadyOpen`, `ItemNotAvailable`

и превращать их в короткий UX-ответ без stacktrace.

### 5.7 `send_or_edit` как preferred mixed-output helper

Если `handler` работает и с `Message`, и с `CallbackQuery`, то default-путь — `send_or_edit(...)`, 
если нет явной причины делать иначе.

### 5.8 Domain routers + local helpers

Хороший паттерн слоя:
- router-файл содержит flow
- `parse/store/load/texts/keyboards` выносятся в `*_helpers`

---

## 6) Handler ↔ Service boundary

### Handler may do

Разрешено:

- проверить, что `callback id` вообще распарсился
- проверить, что текст не пустой
- проверить, что есть нужный FSM-контекст
- показать “ничего не найдено” при `None`
- вызвать `service`
- выбрать UX-ответ
- очистить FSM на terminal branch

### Handler must not do

Запрещено:

- вручную решать `ownership/business permission` как источник истины
- вручную делать `status transition policy`
- решать, доступно ли действие по бизнес-правилам
- подменять `service` доменной проверкой

### Critical rule

UX-guard допустим.  
Бизнес-rule — нет.

То есть:

- `invalid callback payload` → `handler`
- `not participant / transition forbidden / item unavailable by domain rule` → `service`

---

## 7) Handler ↔ FSM boundary

### FSM is UX storage only

FSM может хранить:

- draft fields
- selected ids
- page
- mode
- current step
- ui message ids
- временные флаги сценария

### FSM data rule

Raw FSM dict
- допустим в `handler`
- не должен считаться бизнес-контрактом сервиса

Перед `service call` `handler` обязан, где это важно, привести FSM данные к `Pydantic DTO`.

### State cleanup rule

- terminal branch → `state.clear()`
- recoverable UX-error → `state` обычно не чистится
- cancel-flow → `state.clear()`

---

## 8) Handler ↔ Formatter / Keyboard boundary

### Handler may do

- вызывать `formatter`
- вызывать `keyboard builder`
- локально собрать короткий текст, если он маленький и чисто UX
- передавать `DTO` в `formatter`

### Preferred pattern

По мере роста выносить в `helpers`:

- длинные тексты
- карточки сущностей
- inline keyboard builders
- pagination UI builders

### Handler must not do

- держать в себе длинные смешанные бизнес/UX шаблоны
- повторять крупные `keyboard/view blocks` в разных `handlers`
- превращаться в view-god-file

---

## 9) Exception handling rules

### 9.1 Technical errors

Технические ошибки не должны быть стандартно перехвачены в `handlers`.

Они должны уходить в `global error middleware`. Архитектура фиксирует это прямо: технические ошибки перехватываются 
централизованно, в `handlers` нет `try/except` для техошибок, только для бизнес-ошибок.

### 9.2 Business errors

Локально в `handler` допустимо ловить:
- `ServiceError`
- `NotFoundError`
- domain exceptions, которые нужно превратить в UX-ответ

Но только ради UX-ответа, без stacktrace в пользовательский слой.

### 9.3 Broad `except Exception` in handlers

Broad `except Exception` в `handlers` считается нарушением канона, кроме очень узких, явно оправданных UX-fallback случаев.

### 9.4 Telegram-specific UX fallbacks

Локальные точечные fallback-исключения уровня Telegram client/API допустимы, если они реально связаны с UX-обновлением сообщения, а не с бизнес-логикой.

---

## 10) Callback parsing rules

### Preferred pattern

Использовать единый `helper`-подход для `callback parsing`.

### Required behavior

Любой `callback parsing` должен:

- безопасно валидировать вход
- уметь вернуть `None` / `abort`
- давать короткий UX-ответ при некорректном `payload`

### Not preferred

Raw `str.split()` в каждом `handler`-файле без общего `parsing helper` — переходный стиль, не канон.

---

## 11) ID conventions in handlers

Нужно явно различать:

- `telegram_user_id` / `admin_tg_id` / `callback_user_tg_id` → Telegram ID
- `user_id` / `item_id` / `rental_id` / `review_id` → DB/domain ID

### Rules

- не использовать двусмысленные имена вроде `admin_id`, если это Telegram ID
- не доверять `actor identity` из FSM/raw payload
- `actor identity` брать из `trusted event` / `middleware data`
- `service payload` строить на основе `trusted user identity`

---

## 12) Service payload construction

`Handler` должен передавать в `service`:

- primitive args
- DTO/Pydantic
- trusted actor IDs
- минимально необходимый business input

`Handler` не должен передавать в `service`:

- raw callback string
- raw FSM dict как конечный контракт
- ORM / repository results
- недоверенные actor IDs из пользовательского ввода

---

## 13) Router file structure

Допустимый и уже подтверждённый паттерн:

- router file: flow / entry / orchestration
- local helpers:
  - `parse`
  - `validate`
  - `store/load`
  - `texts`
  - `keyboard`

### Rule

Если router-файл разрастается в god-module, его нужно разгружать в `helpers`, а не тянуть всю UX-логику в один файл.

---

## 14) Middleware assumptions

`Handlers` могут опираться на `middleware-provided data`, если это уже проектный контракт:

- `user`
- `injected services`
- `admin_ids`
- другие глобальные UX/app-level guards

Но скрытые предположения о `middleware` должны быть минимальны и по возможности явно зафиксированы в сигнатуре `handler’а`.

---

## 15) What must not be lifted into canon automatically

Агент обязан различать:

- устойчивый канон `handler-layer`
- переходный стиль
- исторические компромиссы
- сломанные/legacy куски

Не поднимать автоматически до стандарта:

- broad `except Exception` в `handlers`
- импорт `enum/model` из `db.models.*`
- ручной raw `split()` как основной callback-parser
- большие router-файлы как норму
- временные FSM flags / hacks
- legacy / trash `handlers` как reference style

---

## 16) P0 / P1 / P2 for handler review

### P0 — direct architectural violation

Критично:

- direct repository usage in handler
- SQLAlchemy / ORM usage in handler
- business logic / policy / transition rules in handler
- direct import from `db.models.*` into handlers
- broad technical exception handling as normal path
- raw FSM dict used as business contract
- invalid / broken handler code in active router files

### P1 — architectural weakness

Плохо, но не критично:

- слишком толстый handler
- duplicated callback parsing
- inconsistent UX error handling
- formatter/keyboard logic too coupled with handler
- hidden middleware assumptions
- mixed output patterns without local discipline
- handler-specific business checks drifting in
- oversized router files

### P2 — tech debt / cleanup

Не срочно:

- comments noise
- naming inconsistency
- duplicated small helpers
- stale docstrings
- leftover legacy files
- minor FSM cleanup
- stylistic inconsistencies

Если есть P0, агент не должен уводить фокус на P2.

---

## 17) Review checklist for any handler change

Перед тем как предложить новый handler или изменение существующего, агент обязан проверить:

1. Это точно UX/FSM/router слой?
2. Нет ли здесь repo / ORM / SQLAlchemy usage?
3. Нет ли здесь бизнес-решения, которое должен принимать service?
4. Валидируется ли callback/input до service call?
5. Есть ли корректный UX-guard для `None`?
6. Не ловится ли здесь broad `Exception` без крайней необходимости?
7. Технические ошибки действительно уходят в global error middleware?
8. Не передаётся ли raw FSM dict в service как готовый контракт?
9. Нужно ли собрать DTO из FSM/data до service call?
10. Trusted ли actor identity?
11. Не строит ли handler слишком много formatter/keyboard logic внутри себя?
12. Нужен ли `send_or_edit` вместо ручного смешения output API?
13. Не импортируется ли что-то из `db.models.*`?
14. Не превратился ли router-файл в god-module?
15. Не поднимается ли локальный компромисс до общего стандарта?

---

## 18) Output mode for the agent

Если агент анализирует `handlers`, он должен отвечать так:

1. Что уже хорошо
2. Inventory handlers
3. Фактические architectural patterns
4. Transitional exceptions
5. P0 — прямые нарушения
6. P1 — архитектурные слабости
7. P2 — техдолг / cleanup
8. Candidate rules / final rules for handler-layer
9. Open questions / ambiguities

Если агент предлагает изменение:

- не делать массовый рефактор
- предлагать один bounded-step
- не переписывать весь router
- учитывать, что пользователь может вносить правки вручную
- если нужен код — давать готовые фрагменты для ручной вставки

---

## 19) Final principle

Для слоя `handlers/` главный принцип такой:

> `Handler` должен быть UX-сильным, сценарно аккуратным и доменно тупым.

Он:
- принимает пользовательский ввод
- ведёт пользователя по сценарию
- хранит временный UX-контекст
- вызывает сервис
- показывает результат

и не:
- принимает доменные решения
- работает с БД
- знает ORM
- подменяет service-layer