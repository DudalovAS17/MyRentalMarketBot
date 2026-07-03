# Документация по DB-слою и bootstrap

Документ описывает актуальные файлы `db/`: инфраструктуру подключения, bootstrap, базовые модели и ORM-модели проекта.

Текущая доменная модель: компания ведёт каталог товаров для аренды, клиенты создают заявки, менеджеры обрабатывают заявки, отзывы и поддержка связаны с клиентами/товарами/заявками.

---

## 0. Карта файлов `db/`

### Инфраструктура

| Файл | Назначение |
|---|---|
| `db/database.py` | Создаёт async engine/session factory, проверяет соединение, закрывает engine. |
| `db/bootstrap.py` | Startup/shutdown hooks базы: проверить соединение, инициализировать, закрыть. |

---

## 1. `db/database.py`

Модуль подключения к базе данных.

### Что делает

- читает `settings.database_url`;
- создаёт `AsyncEngine` через `create_async_engine(...)`;
- создаёт `async_sessionmaker[AsyncSession]`;
- хранит engine/session factory во внутреннем `_DatabaseState`;
- отдаёт session factory репозиториям;
- проверяет соединение через `SELECT 1`;
- закрывает engine на shutdown.

### `_DatabaseState`

Внутренний объект состояния:
- `engine: AsyncEngine | None`;
- `session_factory: async_sessionmaker[AsyncSession] | None`.

Смысл: держать DB infra в одном месте, а не в нескольких глобальных переменных.

### Функции

> `get_database_url() -> str`
- Возвращает `settings.database_url`.

> `init_db(create_tables: bool = False) -> None`
- Если engine/session factory уже есть — ничего не делает.
- Создаёт `AsyncEngine` с `echo=False`, `future=True`, `pool_pre_ping=True`.
- Создаёт `async_sessionmaker` с `autoflush=False`, `autocommit=False`, `expire_on_commit=False`.
- При `create_tables=True` вызывает `Base.metadata.create_all`.

> `get_session_factory() -> Callable[[], AsyncSession]`
- Возвращает session factory для repositories.
- Если база не инициализирована — выбрасывает `RuntimeError`.

> `check_db_connection() -> bool`
- Создаёт отдельный test engine.
- Выполняет `SELECT 1`.
- Возвращает `True`, если результат `1`.
- При ошибке логирует и возвращает `False`.
- В `finally` dispose-ит test engine.

> `close_db() -> None`
- Dispose-ит engine, если он есть.
- Сбрасывает `_db_state.engine` и `_db_state.session_factory` в `None`.

### Канон слоя

- Repositories получают сессии только через `get_session_factory()`.
- `create_tables=False` — production default; схема БД должна жить через Alembic migrations.
- `create_tables=True` — dev/MVP shortcut, а не основной production-путь.
- `db/database.py` не содержит query/business/Telegram/FSM-логики.

---

## 2. `db/bootstrap.py`

Startup/shutdown orchestration для базы.

### Функции

> `init_db_or_fail(create_tables: bool = False) -> None`

Порядок:
1. вызывает `check_db_connection()`;
2. если соединение не удалось — логирует ошибку и выбрасывает `RuntimeError("Database connection check failed")`;
3. если соединение успешно — вызывает `init_db(create_tables=create_tables)`;
4. логирует успешную инициализацию.

> `shutdown_db() -> None`
- вызывает `close_db()`;
- логирует завершение shutdown.

### Канон

- Bootstrap должен падать явно, если БД недоступна.
- Bootstrap не содержит SQLAlchemy low-level config — это в `db/database.py`.
- Bootstrap не содержит repository/service/business logic.

---

## 3 Практические правила для DB-слоя

1. **Не создавать engine/sessionmaker в repositories.** Только `db/database.py`.
2. **Не использовать `create_all` как production-миграции.** Production default — `create_tables=False` и Alembic.
3. **Не добавлять бизнес-логику в ORM-модели.** Модели описывают структуру, связи и constraints.
4. **Если добавляется поле модели — обновить схему, миграцию, репозиторий/сервис и документацию.**
5. **Если меняется FK/ondelete — проверить каскады и бизнес-эффект.** Например, удаление категории каскадит подкатегории, удаление товара каскадит фото/характеристики, но заявки на товар ограничены `RESTRICT`.