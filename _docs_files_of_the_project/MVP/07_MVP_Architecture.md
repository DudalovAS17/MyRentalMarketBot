# MVP: Архитектура

## 1. Назначение документа

Этот файл фиксирует минимальную архитектуру RentalMarketBot для MVP.

Цель — не построить “идеальную enterprise-систему”, а удержать проект в чистой слоистой структуре, чтобы его можно было развивать без хаоса.

Главная схема:

```text
Telegram update
→ handler
→ service
→ repository
→ database
→ notification
```

---

## 2. Что уже есть в проекте

Текущий проект уже имеет достаточно взрослую архитектуру.

Уже есть:

```text
централизованная регистрация роутеров
отдельные user/admin routers
services
repositories
models
schemas
enums
container / сборка зависимостей
middlewares
NotificationService
AdminAction / audit log
FSM-сценарии
seed/import-скрипты
```

Это хороший фундамент. Архитектуру не нужно ломать и переписывать с нуля.

---

## 3. MVP-слои

Минимальные слои проекта:

```text
handlers
states
keyboards
texts
services
repositories
models
schemas
enums
middlewares
database
notifications
seeds
```

Ответственность:

| Слой | Ответственность |
|---|---|
| handlers | принимают message/callback и вызывают сервисы |
| states | хранят FSM-шаги |
| keyboards | строят inline/reply-кнопки |
| texts | формируют тексты сообщений |
| services | содержат бизнес-логику |
| repositories | работают с БД |
| models | описывают таблицы |
| schemas | валидируют входные/выходные данные |
| enums | фиксируют статусы и типы |
| middlewares | прокидывают user/admin/session/dependencies |
| notifications | отправляют сообщения клиентам/админам |
| seeds | наполняют демо-каталог |

---

## 4. Главное архитектурное правило

Handlers должны быть тонкими.

Правильно:

```text
handler получил callback
→ достал item_id
→ вызвал RentalService
→ показал результат
```

Неправильно:

```text
handler сам валидирует всю заявку
handler сам считает цену
handler сам пишет в БД
handler сам отправляет все уведомления
handler сам решает статусную машину
```

Бизнес-логика должна жить в сервисах.

---

## 5. Минимальные сервисы MVP

Для MVP нужны:

```text
CatalogService
ItemService
PhotoService
RentalService
AdminRentalService
SupportService
NotificationService
UserService
AdminActionService
```

Если они уже существуют, задача — не создать новые, а выровнять ответственность.

---

## 6. Минимальные repositories MVP

Нужны:

```text
CategoryRepository
ItemRepository
ItemPhotoRepository
ItemCharacteristicRepository
RentalRepository
UserRepository
SupportRepository
AdminRepository
AdminActionRepository
```

Repository не должен знать Telegram-логику. Он работает только с данными.

Допустимое исключение для текущего MVP: характеристики товара могут жить внутри `ItemRepository`, 
если они используются только как часть карточки товара и не имеют отдельного пользовательского сценария. 
В таком случае `ItemRepository` всё равно не должен знать Telegram-логику и должен работать только с данными.

---

## 7. Минимальные enums MVP

Нужны:

```text
RentalStatus
ItemStatus
SupportTicketStatus
AdminRole
AccountStatus, если уже используется
```

Для заявки оставить текущие MVP-статусы:

```text
REQUESTED
IN_PROGRESS
CONFIRMED
REJECTED
COMPLETED
CANCELLED_BY_CLIENT
CANCELLED_BY_ADMIN
```

---

## 8. FSM как отдельный слой

FSM нужна для сценариев:

```text
создание заявки
поддержка
админский комментарий
ответ поддержки
создание/редактирование товара, если уже есть
```

Главный приоритет — новая пошаговая FSM заявки:

```text
quantity
period
delivery_needed
delivery_address
client_name
client_phone
client_comment
confirmation
```

---

## 9. Что нужно слегка поправить

### 9.1. Держать бизнес-логику в services

Если в handlers есть длинная логика создания заявки, её нужно постепенно переносить в `RentalService`.

### 9.2. Не расширять старую C2C-логику

Если в коде остались сущности/тексты от старого маркетплейса:

```text
сделки
объявления
арендодатель
модерация объявлений
```

их нужно переименовывать на уровне UI и постепенно на уровне домена.

### 9.3. Не добавлять новые большие фичи до закрытия MVP

Сейчас архитектура должна обслуживать главный поток:

```text
каталог → карточка → заявка → админка → статус → уведомление
```

---

## 10. Что НЕ входит в MVP архитектуры

Пока не обязательно:

```text
микросервисы
очереди Celery/RQ
сложный event bus
отдельная веб-админка
Mini App
полная CRM-интеграция
многоуровневые permissions
сложная аналитика
```

Docker, Alembic, PostgreSQL, Redis — полезны, но приоритет зависит от текущего состояния проекта. Если проект сейчас стабильно работает на текущей БД, не нужно ломать его ради “идеальной” инфраструктуры до завершения MVP.

---

## 11. Критерии готовности архитектуры

Архитектура готова для MVP, если:

```text
новый сценарий можно добавить без хаоса
handlers остаются короткими
business logic живёт в services
repositories не зависят от Telegram
schemas используются для входных данных
статусы вынесены в enums
уведомления идут через NotificationService
ошибки логируются
```

---

## 12. Приоритет

Статус: сильная база уже есть.

Приоритет доработки: поддерживающий.

Главное — не переписывать архитектуру, а аккуратно довести главный MVP-поток на существующем фундаменте.
