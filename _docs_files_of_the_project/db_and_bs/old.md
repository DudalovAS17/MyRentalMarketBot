# [db/database.md]()

## Назначение

`db/database.py` — модуль подключения к базе данных

Он отвечает за:

- создание подключения к базе (`AsyncEngine`)
- создание фабрики сессий (`async_sessionmaker`)
- выдачу фабрики сессий (`session factory`) для слоя repositories
- проверку соединения с БД
- корректное закрытие подключения (`engine`) при остановке приложения (`shutdown`)

Этот файл **не содержит**:

- бизнес-логики
- Telegram/FSM/UI логики
- repository/service логики

---

## Основные сущности

`class _DatabaseState`

`_db_state` - Внутренний объект, который хранит текущее состояние подключения к базе.

- `engine` (`async_engine`)
- `session_factory` (`AsyncSessionLocal`)

> `engine` - используется как единая точка подключения к БД после инициализации.

>  `session_factory` — фабрика сессий для работы с БД.


`class _DatabaseState` сделан, чтобы состояние подключения хранилось **в одном месте**, а не в нескольких отдельных глобальных переменных.

---

## Функции

> `get_database_url()` - возвращает адрес подключения к базе из настроек приложения.

> `init_db()` - [инициализация подключения к БД и создание таблиц]()

- собирает `engine`
- собирает `session_factory`
    
Тут я не разбираю пока, что значат параметры в них при создании.

#### Канон:
- `create_tables=False` — production default (должна жить через миграции, а не через `create_all`)
- `create_tables=True` — DEV/MVP режим: создаём таблицы через `Base.metadata.create_all`

> `get_session_factory()` - [возвращает фабрику сессий для repositories]()

>  `check_db_connection()` - [проверяет доступность БД через `SELECT 1`]()

Использует отдельный test engine и возвращает `bool`.

> `close_db()` - аккуратное закрытие `AsyncEngine` и сброс глобального infra-состояния

Используется на shutdown приложения.

---

## Канон слоя

- repositories получают сессии только через `get_session_factory()`
- `db/database.py` не знает про handlers/services/repositories доменно
- `create_all` не является production-нормой
- shutdown базы должен идти через `close_db()`

---

## Что не делать

- не создавать engine/sessionmaker в repositories
- не вызывать `create_all` как основной production-путь
- не тянуть сюда бизнес-логику
- не использовать этот модуль как место для query-логики


---


# [db/bootstrap.md]()

## Назначение

Он отвечает за:

- проверку доступности БД на старте
- запуск database infra
- аварийный fail-fast, если БД недоступна
- корректный shutdown database infra

Файл **не содержит**:

- SQLAlchemy-конфиг низкого уровня
- repository/service/business logic

---

## Функции

> `init_db_or_fail(create_tables: bool = False)` - стартовый bootstrap-хук базы данных.

Порядок работы:

1. вызывает `check_db_connection()` - проверяем подключение к БД
2. если соединение не удалось — пишет ошибку и выбрасывает `RuntimeError`
3. если соединение успешно — вызывает `init_db()`

#### Канон:
- bootstrap должен падать явно, если БД недоступна
- production default: `create_tables=False`
- миграции важнее, чем `create_all` на старте

> `shutdown_db()` - Shutdown-хук базы данных

Вызывает `close_db()` и завершает database infra корректно.

---

## Канон слоя

- `bootstrap.py` orchestrates lifecycle, но не содержит DB-конфиг низкого уровня
- health-check должен происходить до основной инициализации
- при недоступности БД приложение должно fail-fast
- shutdown базы должен быть явным и отдельным шагом

---

## Что не делать

- не переносить сюда SQLAlchemy query logic
- не добавлять сюда repository/service/business code
- не использовать bootstrap как место для миграционной логики
- не скрывать ошибки подключения к БД