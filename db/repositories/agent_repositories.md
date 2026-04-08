# AGENT: Repositories

## Scope

Этот файл задаёт правила для слоя `db/repositories` в проекте My-Rental-Bot.

Он нужен для любого агента, который:

- анализирует репозитории
- предлагает новые repository-классы
- предлагает изменения существующих repo-методов
- делает review решений в persistence/query-слое (?)
- оценивает границу `service ↔ repository`

Этот файл не про весь проект, а только про слой SQLAlchemy repositories.

---

## 1) Role of repositories

Repository в этом проекте — это:
- слой доступа к БД
- слой SQLAlchemy-запросов и persistence-операций (`create / update / delete / commit / refresh`)
- место для любых SQLAlchemy-операций (`select / join / filter / exists / count / update / delete`)
- место для технической координации ORM-read/write операций
- место для eager loading, если это нужно сервису для корректного read-case
  (eager loading - это предварительная загрузка связанных сущностей сразу в repo-запросе, например есть `Rental`, у которой есть: `item / owner / renter`. 
  Eager loading означает: [загрузи связанные объекты сразу, пока сессия открыта]())
- место для write-операций с `commit / rollback / refresh`
- SQLAlchemy session management (управление сессией)
- возврат ORM-моделей, списков ORM или примитивных значений (`bool, int, scalar/aggregate values`)

Repository **не является**:
- service-слоем
- местом для бизнес-логики
- местом для UI/Telegram/FSM
- DTO/Pydantic boundary
- местом для принятия продуктовых решений
- формирования пользовательских сообщений

Главный принцип:

> Repository знает **как читать и писать данные**, но не знает **зачем бизнес этого хочет**.

> *Repository = чистый доступ к БД. 
Он знает как читать и писать, но не знает зачем.*

---

## 2) Hard boundaries

### Repository layer may contain

Разрешено:

- `AsyncSession`, `select`, `update`, `delete`, `func`, `exists`, `and_`, `or_`, `join` и другие SQLAlchemy primitives
- ORM-модели
- read-запросы любой разумной сложности
- eager loading (`selectinload`, при необходимости другие ORM loader options)
- транзакционные операции (`commit` / `rollback` / `refresh`)
- CRUD-операции
- existence-check / count / aggregate queries
- atomic update queries вида `UPDATE ... WHERE ...`
- write-helper методы в base-repository
- DTO/Pydantic **на входе**, если это упрощает слой service
- `dict` как input только если это уже принято в конкретном repo-контракте и не размывает границу слоя

### Repository layer must not contain

Запрещено:

- Telegram/FSM/UI зависимости
- тексты сообщений
- клавиатуры
- бизнес-правила и policy-level decisions
- whitelist/blacklist доменных переходов
- права доступа уровня приложения
- интерпретация “что должен увидеть пользователь”
- возврат DTO/Pydantic наружу
- оркестрация нескольких сценариев уровня service
- попытки заменить service-слой “умным repo”

---

## 3) Repository boundary relative to other layers

Repositories принадлежат только persistence-слою.

Правило:

- handlers не работают с repo напрямую
- handlers не работают с ORM
- services могут вызывать repo
- repo может знать ORM и SQLAlchemy
- repo не должен знать handlers/services/FSM/Telegram

Наружу из service layer идут DTO/Pydantic, а не ORM.

Следовательно:

- repo может возвращать ORM (или примитивы bool, int, None) в service
- repo не должен проектироваться так, как будто его методы будут вызываться из handlers/UI напрямую

---

## 4) Core contracts of the layer

### 4.1 Input contract (Контракт)

Repository может принимать:

- простые типы (`int`, `str`, `bool`, `datetime`, `Decimal`)
- domain-neutral query arguments
- Create/Update DTO (например, `ItemCreate`, `ItemUpdate`)
- в отдельных случаях `dict`, если это уже часть фактического repo API

Repository не должен принимать:

- `Message`, `CallbackQuery`, `FSMContext`
- Telegram-объекты
- UI-объекты
- handler-specific state

### 4.2 Output contract

Repository возвращает только:

- ORM-объект;
- `Optional[ORM]`
- `list[ORM]`
- примитивы:
  - `bool`
  - `int`
  - `None`
- scalar/aggregate values
  - `count`
  - `avg`
  - tuple/scalar result, если это действительно aggregate/query-result

Repository **никогда не возвращает**:

- DTO/Pydantic
- Telegram-ready payload
- format-ready strings
- user-facing response objects

---

## 5) API conventions

### 5.1 Canonical naming

Канонический минимум:

- `get_by_id`
- `get_by_*`
- `list_*`
- `create`
- `update`
- `delete`

### 5.2 Allowed extended patterns

Допустимо, если это отражает реальный query/use-case:

- `exists_*`
- `count_*`
- `set_*`
- `try_*`
- `has_*`
- `list_recent_*`
- `get_details_*`
- `search`
- `close`
- `touch_*`
- `reorder`
- `swap_*`

### 5.3 Naming principle

Имя repo-метода должно описывать **техническую SQL/persistence операцию**, а не подменять собой product use-case.

Хорошо:

- `exists_for_rental`
- `count_by_item`
- `try_update_status`
- `list_recent_with_details_for_admins`

Плохо:

- `approve_request_if_user_deserves_it`
- `decide_best_owner_action`
- `build_support_message_for_admin`

---

## 6) Transaction rules

### 6.1 MVP transaction law

Проект не использует Unit of Work.

Поэтому каждый write-метод репозитория обязан:

- делать `commit()`;
- при ошибке `commit()` делать `rollback()`;
- пробрасывать исключение выше.

Это жёсткое правило слоя.

### 6.2 Allowed write patterns

Разрешённые канонические write-паттерны:

#### A. load → mutate → commit → refresh

Используется для обычных create/update/delete операций.

Примерно так:

- загрузили ORM;
- изменили поля;
- `commit`;
- `refresh`;
- вернули ORM.

#### B. direct UPDATE ... WHERE ... → commit

Используется для:

- атомарных status/flag updates;
- конкурентных переходов;
- stale-button protection;
- точечных update-операций без необходимости загружать целый ORM-объект.

Возврат обычно:

- `bool` по `rowcount > 0`;
- либо ORM/scalar, если это реально нужно и сделано консистентно.

### 6.3 Refresh rule

`refresh()` обязателен там, где метод возвращает ORM после записи и сервису важно получить актуальное состояние объекта.

### 6.4 No hidden transaction magic

Нельзя:

- скрывать write без `commit`;
- полагаться на то, что кто-то “снаружи потом закоммитит”;
- делать частично завершённые write-методы.

---

## 7) Atomic operations and concurrency

Для конкурентных переходов и флагов repo-слой **может и должен** использовать атомарные SQL-операции.

Это особенно уместно для:

- status transitions;
- confirm flags;
- activation checks;
- stale UI actions;
- race-sensitive mutations.

Разрешённый подход:

- `UPDATE ... WHERE current_state = ...`
- `UPDATE ... WHERE participant_id = ...`
- `UPDATE ... WHERE flag = false`

Возвращать в таких методах предпочтительно:

- `bool` (`успешно / не применилось`);
- или `int` / `rowcount`, если это уже часть контракта.

Но важно:

> repo применяет **технически безопасную mutation-операцию**,  
> а service решает, **когда и почему её вообще можно вызывать**.

---

## 8) Business boundary

Это ключевое правило слоя.

### Repo may contain

Допустимо:

- техническая query-semantics;
- eager loading связей;
- atomic update semantics;
- append-only persistence;
- ordering mutation для дочерних сущностей;
- aggregate/stat queries.

### Repo must not contain

Запрещено:

- решать, допустим ли переход по бизнесу;
- решать, кто имеет право на действие;
- решать, какой статус “правильный” с продуктовой точки зрения;
- реализовывать policy-level workflow;
- интерпретировать бизнес-инварианты шире, чем это нужно для конкретного SQL-условия.

Правильное разделение:

- **service**: “можно ли это делать по правилам продукта?”
- **repo**: “как это сделать в БД корректно и атомарно?”

---

## 9) Eager loading and query shaping

Eager loading в repo разрешён и приветствуется, если:

- сервису для read-case нужен связанный ORM-граф;
- это избавляет service от SQLAlchemy-логики;
- это не превращает repo в UI-builder.

Допустимо:

- `selectinload(...)`
- другие loader options по необходимости

Принцип:

> SQL-форма чтения — ответственность repo,  
> интерпретация результата — ответственность service.

---

## 10) BaseRepository and shared helpers

Если в проекте есть `BaseRepository`, это каноническое место для общих persistence-helper patterns.

Туда уместно выносить:

- session context helper;
- `_list`
- `_one_or_none`
- `_exists`
- `_commit_or_rollback`
- `_add_commit_refresh`
- `_commit_refresh`
- `_delete_commit`
- `_execute_update_commit`

Новые repo-методы по возможности должны опираться на уже существующий базовый каркас, а не изобретать новый стиль локально.

Но:

- BaseRepository не должен превращаться в второй service-layer;
- helper’ы должны оставаться persistence-утилитами, а не доменными policy-механизмами.

---

## 11) ID conventions

Это жёсткое правило проекта.

Нужно строго различать:

- `db_user_id` / `user_id` / `owner_id` / `renter_id` → DB PK/FK
- `telegram_user_id` / `telegram_id` / `admin_tg_id` / `closed_by_admin_tg_id` → внешний Telegram ID

### Rules

- Никогда не смешивать DB ID и Telegram ID.
- Если метод работает по Telegram ID, это должно быть видно по имени аргумента и/или метода.
- Избегать нейтральных имён вроде `admin_id`, если фактически это Telegram ID.
- Контракт service↔repo по типу ID должен быть однозначным.

### Good examples

- `get_by_telegram_id(...)`
- `exists_by_telegram_id(...)`
- `list_by_user_id(...)`

### Bad examples

- `admin_id`, если это tg-id
- `user_id`, если это telegram id
- разный смысл одного и того же имени аргумента в service и repo

---

## 12) Time conventions

Во всём repo-слое используется только aware UTC datetime.

Разрешено:
```python
from datetime import datetime, timezone
datetime.now(timezone.utc)
```

Запрещено:
- `datetime.now()` без `timezone`;
- `datetime.utcnow()`;
- локальное время;
- timezone conversion;
- форматирование времени “для человека”.

Repository может:
- писать aware UTC timestamps;
- сравнивать aware UTC timestamps;
- использовать время как технический критерий в запросах.

Repository не должен:
- локализовывать время;
- форматировать время для UI;
- принимать timezone/product-display решения.

## 13) Update conventions
### 13.1 Partial update

Если repo принимает Update DTO, partial update должен опираться на:
```
model_dump(exclude_unset=True)
```

Это важно, чтобы различать:
- поле не было передано;
- поле было передано явно как null.

### 13.2 Empty patch

Если patch пустой, repo должен вести себя предсказуемо и консистентно внутри своего контракта.

Допустимы два подхода:
- вернуть текущий ORM без commit;
- либо использовать уже принятый в конкретном repo-base pattern.

Но нельзя делать это хаотично от метода к методу без причины.

### 13.3 No implicit DTO-out

Даже если update принимал DTO, возвращать наружу он должен ORM или primitive, но не DTO.


## 14) Aggregates / existence / append-only repositories

Не все repositories обязаны быть полным CRUD.

### Разрешены специализированные контракты
Append-only repo

Например audit/event repository:
- только create
- без update/delete

**Restricted-write repo**

Например support/history-like сущности:
- create
- ограниченные write-методы (close, touch_*)
- без полного CRUD по design

**Aggregate/stat repo methods**

Допустимы методы вроде:
- exists_*
- count_*
- get_stats_*

Это нормальная часть repo-слоя, если метод реально отвечает на persistence/query-вопрос.

## 15) Comments inside repositories

Комментарии в repo допустимы только если они:
- объясняют нетривиальную SQL/transaction семантику;
- объясняют race/concurrency reasoning;
- объясняют why this eager loading exists;
- фиксируют важный persistence contract.

Не засорять repository-код:
- черновыми размышлениями;
- эмоциональными пометками;
- “вставил без осознания”;
- длинными TODO-блоками;
- историческими спорами прямо в рабочем коде.

Если комментарий не помогает понять SQL/persistence-логику, он не должен жить в repo.


## 16) Transitional exceptions

Агент обязан различать:
- канон слоя repositories;
- фактические временные исключения;
- прямые архитектурные нарушения.

Не превращать автоматически в стандарт
- локальные исторические naming-компромиссы;
- смешанный стиль `_sf()` vs `_session()`, если слой ещё не выровнен;
- случайный from `__future__` import annotations в repo без реальной необходимости;
- отдельные доменно-окрашенные методы, если они достались исторически;
- комментарии/доки переходного периода.

Если что-то встречается в коде, это ещё не значит, что это нужно повторять в новых repository-модулях.


## 17) P0 / P1 / P2 for repository review

### P0 — direct architectural violation
Критично:
- Telegram/FSM/UI внутри repo;
- бизнес-логика в repo;
- возврат DTO/Pydantic из repo;
- write-метод без rollback на commit-error;
- смешение DB ID и Telegram ID в сигнатурах/контрактах;
- runtime-contract mismatch между service и repo;
- запись в несуществующее ORM-поле;
- naive datetime / timezone misuse;
- repo начинает принимать решения уровня приложения.

### P1 — architectural weakness / inconsistency
Не критично, но плохо:
- эрозия границы между repo и service;
- слишком доменно-нагруженные имена/методы;
- неоднородный transaction/update style;
- неясный контракт empty-patch update;
- naming ambiguity у ID;
- несогласованный session helper style;
- шумные комментарии;
- eager loading без явной пользы.

### P2 — tech debt / cleanup
Не срочно:
- formatting;
- imports order;
- унификация type hints;
- косметическая зачистка комментариев;
- локальная унификация helper-style.

Если есть P0, агент не должен уводить фокус на P2.

## 18) Review checklist for any repository change

Перед тем как предложить новый repo или изменение существующего, агент обязан проверить:
- Это действительно persistence/query logic, а не service logic?
- Нет ли Telegram/FSM/UI зависимостей?
- Не протекла ли бизнес-логика в repo?
- Возвращает ли repo только ORM/primitive?
- Не возвращается ли DTO/Pydantic?
- Есть ли rollback при commit-error?
- Нужен ли refresh после write?
- Можно ли здесь безопасно использовать atomic UPDATE ... WHERE ...?
- Ясно ли различены DB ID и Telegram ID?
- Нет ли contract mismatch между service и repo сигнатурой?
- Используется ли aware UTC datetime?
- Нужен ли eager loading, или он лишний?
- Является ли метод реально query/persistence операцией, а не скрытым service use-case?
- Не поднимается ли локальный исторический компромисс до уровня нового стандарта?
- Можно ли переиспользовать BaseRepository/helper вместо нового локального велосипеда?

## 19) Output mode for the agent

Если агент анализирует repositories, он должен отвечать так:
- Что уже хорошо
- P0 — прямые нарушения
- P1 — архитектурные слабости
- P2 — техдолг / чистка
- Один лучший следующий шаг
- Что не нужно трогать сейчас

Если агент предлагает изменение:
- не делать массовый рефактор;
- предлагать один bounded-step;
- учитывать, что пользователь может вносить изменения вручную;
- не подменять анализ переписыванием всего слоя;
- если нужен код — давать готовые фрагменты для ручной вставки.

## 20) Final principle

Для слоя db/repositories главный принцип такой:
```
Repository должен быть технически сильным, транзакционно надёжным и архитектурно скучным.
```
Чем меньше repo принимает продуктовых решений, тем лучше.

Repository может быть сложным по SQL, но он не должен становиться “скрытым service-слоем”.


