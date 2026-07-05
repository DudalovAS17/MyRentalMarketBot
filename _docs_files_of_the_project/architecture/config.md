# Назначение

`config.py` — единый typed config приложения. Единый объект настроек приложения?

Читает настройки из ENV/.env, валидирует их при старте и отдаёт уже нормализованные значения в main/container/middlewares.

Он отвечает за:
- чтение `.env` / ENV;
- валидацию обязательных настроек;
- парсинг `ADMIN_IDS`;
- сборку `database_url`;
- хранение Telegram token как `SecretStr`;
- выдачу singleton `settings`.

#### Основные элементы:
- `BASE_DIR` - Путь к корню файла `config.py`. Используется для построения пути к `.env`.
- `ENV_FILE` - Файл окружения проекта.

---

# Отвечает за конфигурацию приложения:

```text
.env / ENV variables
    ↓
Settings(BaseSettings)
    ↓
validation / parsing / normalization
    ↓
settings singleton
    ↓
main.py / container / middlewares use settings
```

Файл не должен содержать бизнес-логику. Его задача — безопасно прочитать настройки и упасть на старте, если конфиг некорректный.


---

# `class Settings(BaseSettings)`

Главный класс настроек.

Наследуется от `BaseSettings`, поэтому умеет читать значения из ENV и `.env`.


## `model_config = SettingsConfigDict()`

| Параметр            | Значение   | Смысл                                                      |
|---------------------|------------|------------------------------------------------------------|
| `env_file`          | `ENV_FILE` | читать `.env` из корня проекта                             |
| `env_file_encoding` | `utf-8`    | корректная кодировка `.env`                                |
| `extra`             | `ignore`   | не падать от лишних env-переменных                         |
| `case_sensitive`    | `False`    | env aliases не зависят от регистра                         |
| `enable_decoding`   | `False`    | отключаем JSON-decode для complex типов - **[костыль?]()** |

`enable_decoding=False` особенно полезен для `ADMIN_IDS`, потому что там используется свой parser.

## Runtime settings

#### `log_level` - Уровень логирования.
- Поддерживает: `DEBUG/INFO/WARNING/ERROR/CRITICAL`
- Если `LOG_LEVEL` не задан, используется `INFO`.

#### `drop_pending_updates` - Управляет поведением при запуске polling.
- Если `True`, бот удалит накопленные updates перед стартом. Полезно при разработке, если накопились старые callback/message updates.

## Telegram settings

#### `telegram_token` - Обязательный Telegram Bot token.

- Хранится как `SecretStr`, чтобы случайно не светить token в repr/logs.
- `token_value()` - Возвращает token как обычную строку.
  - Используется в `main.py` при создании `Bot`: `Bot(token=settings.token_value, ...)`
- `validate_telegram_token()`- Проверяет, что `TELEGRAM_TOKEN` не пустой. Если пустой — приложение падает на старте.

## Admin settings

#### `admin_ids` - Список Telegram ID, которым разрешён вход в админку.
- `ADMIN_IDS` — это guard доступа
- `admins table` — это FK/audit profile
- `parse_admin_ids()` - Парсит `ADMIN_IDS` из разных форматов.

Поведение при пустом `ADMIN_IDS`: пустой `ADMIN_IDS` не ломает приложение.
Но админка будет фактически недоступна. Warning логируется через: `log_startup_warnings()`

## PostgreSQL settings

| ENV-переменные      | Обязательно | Default               | Назначение      |
|---------------------|------------:|-----------------------|-----------------|
| `POSTGRES_USER`     |         нет | `postgres`            | пользователь БД |
| `POSTGRES_PASSWORD` |          да | —                     | пароль БД       |
| `POSTGRES_DB`       |         нет | `aiogram-rentals-bot` | имя базы        |
| `DB_HOST`           |         нет | `postgres`            | host БД         |
| `DB_PORT`           |         нет | `5432`                | port БД         |

- `database_url` - собирает SQLAlchemy async URL. Используется в DB layer.
- `validate_db_password()` - проверяет, что `POSTGRES_PASSWORD` не пустой.  Если пароль пустой — приложение падает на старте.
- `validate_non_empty_string()` - проверяет, что строковые DB-настройки не пустые.
- `parse_db_port()` - Парсит `DB_PORT`.

---




---

## `parse_admin_ids`

`@field_validator("admin_ids", mode="before")` - ?

`parse_admin_ids(cls, admin_ids)-> set[int]`

В идеале должен поддерживать варианты (у меня пока меньше):
- `ADMIN_IDS=""`
- `ADMIN_IDS="123"`
- `ADMIN_IDS="123,456"`
- `ADMIN_IDS="123, 456, 789"`
- `ADMIN_IDS="123 456 789"`
- `ADMIN_IDS="123;456;789"`
- `set/list/tuple[int | str]`

```python
    if admin_ids in (None, "", [], (), set()): # None / "" / пустые контейнеры -> пустое множество
        return set() # Это безопасно: приложение стартует, просто админка выключена.
```

>Если кто-то передал список/кортеж/сет вручную
>```python
>if isinstance(admin_ids, (list, tuple, set)):
>    return {int(x) for x in admin_ids if x is not None and str(x).strip()}
>```
>
> `strip()` - отбрасываем пустые/пробельные значения `"", " "` (убирает и табы/переводы строк)
> 
> Пример: `[1, " 2 ", None, ""] → {1, 2}`

> Если внутри будет `"foo" → int("foo")` бросит `ValueError` → приложение упадёт на старте.
>
> Это intentional: кривой конфиг лучше обнаружить сразу.

> `ENV` почти всегда строка: `"1, 2,3"`
>```python
>s = str(admin_ids).strip()
>if not s:
>    return set()
>```

>```python
>return {int(x.strip()) for x in s.split(",") if x.strip()}
>```
> `split(",")` - разбивает строку по запятым `"123,456,789" → split → ["123", "456", "789"]`

> Если `"1, 2,3 "`:
> - `str(admin_ids).strip() → "1, 2,3"`
> - `split(",") → ["1", " 2", "3"]`
> - `x.strip() → "1", "2", "3"`
> - `int(...) → 1, 2, 3`
> - `set → {1,2,3}`

---

# `get_settings()`

Создаёт singleton настроек.

- `@lru_cache(maxsize=1)` - Чтобы `.env` не читался каждый раз при импортах.
- `ENV` читается один раз при старте приложения, middleware/handlers не читают `ENV` каждый раз

---

# `settings`

Все части проекта используют один объект:

```python
settings: Final[Settings] = get_settings()
```

---

# `config.py`

- Не хранить бизнес-логику.
- Не импортировать aiogram.
- Не создавать bot/dispatcher.
- Не подключаться к БД.
- Только читать, валидировать и нормализовать настройки.

---

# Декораторы 

Специальные “надстройки” над функциями/методами, которые меняют их поведение.

1. `@property`
2. `@computed_field`
3. `@field_validator`
4. `@field_validator(..., mode="before")`
5. `@classmethod`
6. `@lru_cache`

Изучи!