# MyRentalMarketBot

Telegram-бот для MVP сервиса аренды строительного инструмента и техники. Пользователь выбирает товар из каталога, оформляет заявку на аренду, а администратор видит заявку и управляет статусами сделки.

## Основные сценарии MVP

### Пользовательский сценарий

1. Пользователь открывает бота и проходит регистрацию/профиль.
2. Открывает каталог по категориям.
3. Выбирает карточку товара, смотрит описание, цену и фото.
4. Создает заявку на аренду.
5. Получает уведомления по изменению статуса заявки.

### Админский сценарий

1. Telegram ID администратора добавлен в `ADMIN_IDS`.
2. Администратор открывает админ-меню в боте.
3. Просматривает новые заявки.
4. Подтверждает, отклоняет или меняет статус сделки.
5. При необходимости управляет товарами, модерацией пользователей и поддержкой.

## Роли

- **Гость/пользователь** — регистрация, просмотр каталога, поиск, создание заявок, профиль, поддержка.
- **Администратор** — доступ по whitelist из `ADMIN_IDS`, обработка заявок, модерация, управление каталогом и поддержкой.

## Требования

- Python 3.11+
- PostgreSQL 16+ или Docker Compose
- Telegram Bot API token от `@BotFather`

## Быстрый запуск MVP локально

### 1. Установить зависимости

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Настроить `.env`

```bash
cp .env.example .env
```

Заполните минимум:

```env
BOT_TOKEN=<telegram-token-from-botfather>
ADMIN_IDS=123456789
POSTGRES_PASSWORD=postgres
```

Можно использовать единый `DATABASE_URL` вместо `POSTGRES_*`:

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5433/rental_market_bot
```

`BOT_TOKEN` — основной ключ для MVP. Старое имя `TELEGRAM_TOKEN` также поддерживается для совместимости.

### 3. Поднять PostgreSQL через Docker Compose

```bash
docker compose up -d postgres
```

По умолчанию БД доступна на `localhost:5433`, а внутри compose-сети — на `postgres:5432`.

### 4. Создать/обновить схему БД

```bash
alembic upgrade head
```

### 5. Загрузить demo-каталог

```bash
python scripts/seed_demo_catalog.py
```

Команда последовательно загружает категории, товары/фото и характеристики demo-каталога.

### 6. Запустить бота в MVP polling-режиме

```bash
python main.py
```

Для MVP используется polling (`DEBUG=True`). Production webhook, reverse proxy и HTTPS не блокируют MVP и могут быть добавлены позже.

## Docker-запуск всего приложения

```bash
docker compose up --build
```

Для первичной подготовки БД в compose можно выполнить:

```bash
docker compose run --rm bot alembic upgrade head
docker compose run --rm bot python scripts/seed_demo_catalog.py
```

## Команды и точки входа

- `python main.py` — запуск Telegram-бота в polling-режиме.
- `alembic upgrade head` — применить миграции БД.
- `python scripts/seed_demo_catalog.py` — загрузить demo-каталог.
- `docker compose up -d postgres` — поднять только PostgreSQL.
- `docker compose up --build` — поднять весь стек из `docker-compose.yml`.

## Storage

Каталог `storage/` используется для импортированных/local фото demo-каталога. Переменная `STORAGE_PATH=storage` зафиксирована в `.env.example`; отсутствие новых runtime-файлов в `storage/` не должно ломать запуск, потому что demo-данные в БД используют URL/Telegram file ID и seed-скрипты работают отдельно.

## Проверка после запуска

1. Напишите боту `/start`.
2. Откройте каталог и проверьте, что отображаются категории demo-каталога.
3. Откройте карточку товара и проверьте цену/описание/фото.
4. Создайте тестовую заявку на аренду.
5. Зайдите в админский сценарий с аккаунта из `ADMIN_IDS`.
6. Найдите заявку и измените ее статус.
7. Убедитесь, что пользователь получает уведомление о статусе.

## Безопасность конфигурации

- Реальные `.env` и `*.env` игнорируются Git.
- `.env.example` содержит только пустые или демонстрационные значения.
- Не коммитьте реальные токены Telegram, пароли БД и chat ID production-чатов.