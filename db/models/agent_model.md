# AGENT: Models

## Scope

Этот файл задаёт правила для слоя `db/models` в проекте My-Rental-Bot.

Он нужен для любого агента, который:

* анализирует ORM-модели;
* предлагает новые модели;
* предлагает изменения существующих моделей;
* делает review решений в ORM-слое.

Этот файл не про весь проект, а только про слой SQLAlchemy ORM.

---

## 1) Role of models

ORM-модель в этом проекте — это:

* описание таблицы;
* описание полей;
* описание связей;
* описание `ForeignKey`, `CheckConstraint`, `UniqueConstraint`, `Index`;
* минимальная структурная логика данных, если она действительно относится к persistence-слою.

ORM-модель **не является**:

* DTO;
* UI-моделью;
* Telegram-моделью;
* местом для бизнес-логики;
* местом для сериализации.

---

## 2) Hard boundaries

### Model layer may contain

Разрешено:

* `Base`, `TimestampMixin`;
* `Mapped[...]`, `mapped_column(...)`, `relationship(...)`;
* `ForeignKey`, `CheckConstraint`, `UniqueConstraint`, `Index`;
* `SAEnum(...)`;
* `DateTime(timezone=True)`;
* `Numeric(...)`, `BigInteger`, `JSON`, `Text`, `String`, `Boolean` и другие ORM-типы;
* комментарии только если они объясняют **persisted structure** или важную delete/index/constraint семантику.

### Model layer must not contain

Запрещено:

* Telegram/FSM/UI зависимости;
* бизнес-логика;
* статусные переходы;
* сервисные правила;
* `to_dict`, JSON-сериализация, форматирование;
* “умные” методы представления данных для UI/API;
* логику, завязанную на handlers/services;
* доменные решения, которые должны жить в service layer.

---

## 3) ORM boundary relative to other layers

Модели принадлежат только DB layer.

Правило:

* handlers не работают с ORM;
* services не возвращают ORM наружу;
* наружу из service layer идут DTO/Pydantic, а не ORM.

Агент не должен предлагать проектировать ORM так, будто её будут напрямую использовать в handlers/UI.

---

## 4) Base and mixins

### Base

Все ORM-модели проекта наследуются от `Base`.

`Base` задаёт единый `naming_convention` для:

* `pk`
* `fk`
* `ix`
* `uq`
* `ck`

Это канон проекта.

### TimestampMixin

Для большинства доменных моделей используется `TimestampMixin`.

Канон:

* `created_at`
* `updated_at`
* `DateTime(timezone=True)`
* `nullable=False`
* `server_default=func.now()`
* `onupdate=func.now()` для `updated_at`

### Не считать каноном

Не считать стандартом:

* `DictMixin`
* сериализационные mixin’ы
* “умные” `ReprMixin`, если они начинают тащить доменный смысл

Если в старых шаблонах или исторических файлах это встречается, это не значит, что это нужно повторять в новых моделях.

---

## 5) Field conventions

### 5.1 Primary key

Канонический PK:

* `id: Mapped[int]`
* `Integer`
* `primary_key=True`
* `autoincrement=True`

Не изобретать альтернативы без явной причины.

### 5.2 Foreign keys

Foreign key должен быть:

* явным;
* с осмысленным `ondelete`;
* с понятной семантикой данных.

FK нельзя оставлять “по умолчанию”, если от delete-поведения зависит целостность истории.

### 5.3 Nullable

`nullable` задаётся осознанно.

Не использовать `Optional[...]` вместе с `nullable=False`.
Тип и nullable должны говорить одно и то же.

### 5.4 Defaults

Допустимы:

* `default=...` для обычных business-neutral persisted полей;
* `server_default=...` там, где значение должно гарантироваться БД.

Не превращать `default` в скрытую бизнес-логику.

### 5.5 Enum fields

Enum-поля оформляются через:

* `SAEnum(EnumClass, name="db_enum_name")`
* `nullable=False`
* `default=...` если нужен дефолт

Не использовать строковые статусы вместо enum там, где уже существует boundary enum.

### 5.6 Monetary fields

Денежные поля:

* через `Decimal`
* через `Numeric(precision, scale)`

Не использовать `float` для денег.

### 5.7 Datetime fields

Все datetime-поля в ORM:

* только `DateTime(timezone=True)`
* только aware
* только UTC как стандарт хранения

```
from datetime import datetime, timezone
✅ datetime.now(timezone.utc) # это aware и UTC
```

В ORM запрещено:

* naive datetime
* локальное время
* timezone conversion
* timezone=False
* форматирование для человека

```
❌ datetime.now() (→ naive)
❌ datetime.utcnow() (→ naive)
```

«TZ-конвертации разрешены только на границе вывода (UI/API-представление), но не в хранении и не в доменной логике»

---

## 6) ID conventions

Это жёсткое правило проекта.

### Различать:

* `id` / `user_id` / `owner_id` / `renter_id` / `reviewer_id` / `reviewee_id` → это DB primary key / FK на DB сущность
* `telegram_id` / `*_tg_id` → это внешний Telegram ID

Никогда не смешивать эти типы идентификаторов.

### Telegram IDs

Telegram ID хранится как:

* `BigInteger`

Не использовать обычный `Integer` для Telegram ID.

### Naming rule

Если поле хранит Telegram ID, это должно быть видно по имени:

* `telegram_id`
* `admin_tg_id`
* `closed_by_admin_tg_id`

Если поле хранит DB FK, имя должно вести к DB сущности:

* `user_id`
* `owner_id`
* `banned_by_admin_id`

Агент обязан проверять, не путает ли имя поля внешний ID и внутренний DB ID.

---

## 7) Relationship conventions

Relationship в проекте не является полностью догматизированным слоем, поэтому здесь действует не “один рецепт на всё”, а осмысленный выбор.

### 7.1 General rule

Связь должна быть:

* понятной;
* типизированной;
* отражать фактическую ownership/delete семантику.

### 7.2 Prefer

Предпочтительно:

* явная типизация `Mapped[...]`
* `back_populates`, если связь реально двусторонняя и нужна с обеих сторон
* симметричность, если обе стороны реально используются

### 7.3 Allowed

Допустима односторонняя связь, если:

* обратная сторона не нужна;
* её добавление не даёт ценности;
* отсутствие симметрии не ломает читаемость модели.

### 7.4 Cascade / passive_deletes / single_parent

Это не универсальная догма.

Агент должен выбирать их по смыслу:

* `cascade="all, delete-orphan"` — для настоящих дочерних сущностей, которые не живут вне родителя;
* `single_parent=True` — если delete-orphan требует реального единственного владельца;
* `passive_deletes=True` — когда проект осознанно полагается на delete-поведение БД и это согласовано с FK `ondelete`.

Запрещено механически добавлять:

* `cascade`
* `single_parent`
* `passive_deletes`

во все связи подряд.

---

## 8) Delete semantics

Выбор `ondelete` должен быть доменно осмысленным.

### Использовать как правило выбора:

* `RESTRICT` — для истории, сделок, отзывов, репутации, поддержки и других исторически значимых сущностей;
* `CASCADE` — для настоящих дочерних/временных сущностей, которые не имеют смысла без родителя;
* `SET NULL` — для мягких опциональных ссылок.

Агент должен проверять:

* соответствует ли `ondelete` смыслу данных;
* не удаляется ли исторически значимая сущность слишком агрессивно;
* не остаются ли сироты там, где их быть не должно.

---

## 9) Constraints and indexes

### 9.1 Constraints

Инварианты данных должны по возможности жить в БД:

* `CheckConstraint`
* `UniqueConstraint`

Если инвариант можно выразить на уровне таблицы, ORM-модель должна это делать.

### 9.2 Indexes

Индексы задаются явно через:

* `__table_args__ = (Index(...), ...)`

### 9.3 Forbidden

Не использовать `index=True` как стандарт проекта.

Причина:

* проект использует явные именованные индексы;
* смешение `index=True` и `Index(...)` создаёт мусор и дубли.

### 9.4 Composite indexes

Композитные индексы приветствуются, если они отражают реальные запросы:

* history lookups
* status filters
* parent-child selection
* common admin queries

---

## 10) Comments inside models

Комментарии в ORM допустимы только если они:

* объясняют delete semantics;
* объясняют важный constraint;
* объясняют нетривиальную связь;
* фиксируют важное persisted-domain решение.

Не засорять модель:

* дорожной картой;
* большими TODO-блоками;
* списками “будущих полей”;
* длинными размышлениями;
* альтернативными историческими реализациями.

Если комментарий не помогает понять структуру данных, он не должен жить в ORM-модели.

---

## 11) Transitional exceptions

Агент должен различать:

* канон слоя,
* и фактические временные/исторические исключения.

### Не превращать автоматически в стандарт:

* денормализованные snapshot-поля, если они живут в одной конкретной модели как временный или локальный компромисс;
* переходные поля, про которые в коде уже сказано, что они будут удаляться;
* исторические комментарии/закомментированные куски;
* несогласованные relationship-patterns, если проект их ещё не выровнял.

Примеры таких вещей нельзя автоматически поднимать до уровня правила для новых моделей.

---

## 12) P0 / P1 / P2 for model review

### P0 — direct architectural violation

Критично:

* Telegram/FSM/UI внутри ORM;
* бизнес-логика в модели;
* сериализация / `to_dict` / JSON formatting в ORM;
* смешение DB ID и Telegram ID;
* naive datetime или `DateTime(timezone=False)`;
* модель проектируется как DTO/UI object, а не как persistence structure;
* отсутствие осмысленного `ondelete` там, где delete semantics критичны.

### P1 — architectural weakness / inconsistency

Не критично, но плохо:

* неоднородный стиль relationship;
* naming ambiguity между DB ID и Telegram ID;
* несогласованный style defaults/cascade/passive_deletes;
* слабая или шумная структура комментариев;
* частично переходные поля и неочевидные компромиссы.

### P2 — tech debt / cleanup

Не срочно:

* formatting;
* imports order;
* мелкая типизация relationship;
* локальная зачистка комментариев;
* косметическая унификация стиля.

Если есть P0, агент не должен уводить фокус на P2.

---

## 13) Review checklist for any model

Перед тем как предложить новую модель или изменение существующей, агент обязан проверить:

1. Это действительно persistence structure, а не бизнес-объект?
2. Нет ли Telegram/FSM/UI/business logic внутри модели?
3. Явно ли различены DB IDs и Telegram IDs?
4. Telegram IDs точно `BigInteger`?
5. Все datetime-поля `DateTime(timezone=True)`?
6. Осмыслен ли каждый `ondelete`?
7. Нужны ли `CheckConstraint` / `UniqueConstraint`?
8. Индексы заданы явно через `__table_args__`?
9. Не добавляется ли `index=True`?
10. Enum оформлен через `SAEnum(..., name="...")`?
11. Relationship типизирована и понятна?
12. Не предлагается ли временный исторический компромисс как новый стандарт?
13. Комментарии помогают понять структуру данных, а не засоряют модель?

---

## 14) Output mode for the agent

Если агент анализирует модели, он должен отвечать так:

1. Что уже хорошо
2. P0 — прямые нарушения
3. P1 — архитектурные слабости
4. P2 — техдолг / чистка
5. Один лучший следующий шаг
6. Что не нужно трогать сейчас

Если агент предлагает изменение:

* не делать массовый рефактор;
* предлагать один bounded-step;
* учитывать, что пользователь может вносить изменения вручную;
* не подменять анализ переписыванием всего слоя.

---

## 15) Final principle

Для слоя `db/models` главный принцип такой:

> ORM-модель должна быть структурно строгой, скучной и предсказуемой.

Чем меньше в модели “умного поведения”, тем лучше.
Модель должна надёжно описывать данные и их целостность, а не принимать продуктовые решения за service layer.
