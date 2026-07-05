## Назначение

`main.py` — главный файл запуска aiogram-бота.

Он отвечает за:

- настройку логирования;
- проверку доступности БД;
- создание `Bot`;
- создание `Dispatcher`;
- подключение routers;
- создание repositories/services через `app.container`;
- bootstrap профилей админов из `ADMIN_IDS`;
- регистрацию middlewares;
- запуск polling;
- безопасное закрытие bot session и DB engine.

---

## Отвечает за жизненный цикл приложения:

```text
start application
    ↓
configure logging
    ↓
validate/read settings
    ↓
init database
    ↓
create Bot
    ↓
create Dispatcher
    ↓
register routers
    ↓
build services/repositories
    ↓
sync admin profiles from ADMIN_IDS
    ↓
register middlewares
    ↓
delete webhook
    ↓
start polling
    ↓
graceful shutdown
```

Это главный composition root: здесь приложение собирается в рабочий Telegram-бот.

---

## `configure_logging()`

Настраивает глобальное логирование

Использует: `settings.log_level_value`


Почему это важно:
Логирование должно включаться до startup-предупреждений и до запуска приложения.

Правильный порядок:

```text
configure_logging()
settings.log_startup_warnings()
build_app()
```

Так warning про пустой `ADMIN_IDS` будет нормально отображаться в логах.

---

## `build_app()`


Это главная функция сборки приложения.

Делает всю startup-сборку:
- проверяет доступность БД;
- создаёт Bot/Dispatcher;
- подключает routers;
- собирает repositories/services;
- синхронизирует admin profiles из ADMIN_IDS;
- регистрирует middlewares.

#### Последовательность:

1. `await init_db_or_fail()` - [Проверяет доступность БД]()
    - Если PostgreSQL недоступен — приложение падает на старте.
2. `bot` - [Создаёт aiogram `Bot`]()
    - `ParseMode.HTML` - В проекте активно используются HTML-сообщения, поэтому HTML parse mode задаётся глобально для всего бота.
3. `dp` - [Создаёт `Dispatcher` с `MemoryStorage`]()
    - `MemoryStorage` теряет FSM state после перезапуска приложения. Для production позже можно заменить на Redis.
    - управляет routers, middlewares и polling
4. `register_routers(dp)` - [Подключение routers]()
5. `session_factory` - [передаётся в repositories/services]() (handlers не должны работать с БД напрямую)
6. `services` - [Сборка services]()
    - `build_services()` создаёт объект `AppServices`. Через него middleware потом прокидывает сервисы в handlers.
7. `await services.admin_..` - [Bootstrap админов]()
    - В проекте есть две разные сущности:
       - `ADMIN_IDS` → решает, кто может войти в админку
       - `admins.id` → внутренний FK/audit profile сотрудника
         - `sync_admins_from_settings()` [гарантирует, что каждый Telegram ID из `.env` имеет внутреннюю запись в таблице `admins`]().
8. `register_middlewares(...)` - [Регистрация middlewares]()
9. return bot, dp


Важно: если после `bot = await create_bot()` внутри `build_app()` произойдёт ошибка, bot session нужно закрыть. Поэтому в улучшенной версии есть `try/except` вокруг startup-сборки.

---

## `main()` - Запустить Telegram-бота в polling-режиме.

#### Последовательность:
1. `configure_logging()`
2. `settings.log_startup_warnings()`
3. `build_app()`
4. `delete_webhook()` - Зачем: если раньше бот работал через webhook, polling может конфликтовать с ним.
   - `delete_webhook()` гарантирует, что бот работает именно в polling-режиме.
   - `drop_pending_updates` управляет тем, удалять ли старые накопленные updates.
5. `start_polling()`
   - `resolve_used_update_types()` автоматически определяет, какие update types реально используются routers.
6. `shutdown_application()` - Закрывает:
   - Telegram Bot session.
   - DB engine.

Даже если приложение падает с ошибкой, `finally` в `main()` вызывает shutdown.

---

## `main.py`

- Не хранить бизнес-логику.
- Не работать напрямую с моделями.
- Не создавать repositories вручную вне `build_services()`.
- Не читать `.env` напрямую.
- Не проверять админский доступ вручную.
- Только собрать приложение и запустить polling.