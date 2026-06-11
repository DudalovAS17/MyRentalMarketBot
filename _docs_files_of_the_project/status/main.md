# Единая документация по статусам проекта

Документ объединяет актуальные статусы проекта

- `status/admin_status.py` — роли админов, типы audit-действий и типы сущностей для audit-журнала.
- `status/item_status.py` — lifecycle товара каталога.
- `status/rental_status.py` — lifecycle клиентской заявки на аренду.
- `status/review_status.py` — moderation lifecycle отзыва.
- `status/support_ticket_status.py` — lifecycle обращения в поддержку.
- `status/user_status.py` — доступ пользователя/админа через статус аккаунта.


---

## 1. `User`: `AccountStatus`

`AccountStatus` используется и для клиентов (`User.account_status`), и для админов/сотрудников (`Admin.account_status`). Это базовый статус доступа к боту/админке.

| Статус | Значение в БД | Смысл | Терминальность |
|---|---:|---|---|
| `ACTIVE` | `ACTIVE` | Аккаунт активен; пользователь/админ может пользоваться доступными функциями. | Не терминальный |
| `BANNED` | `BANNED` | Аккаунт заблокирован админом; пользоваться ботом нельзя. | Не терминальный, потому что можно вернуть в `ACTIVE` |

### Разрешённые переходы

```text
ACTIVE -> BANNED
BANNED -> ACTIVE
```

Переходы проверяются через `can_transition(old_status, new_status)` и таблицу `ALLOWED_STATUS_TRANSITIONS`.

### Бизнес-смысл

- `ACTIVE` — нормальное состояние аккаунта.
- `BANNED` — административная блокировка.
- При бане у клиента есть audit-поля в модели `User`: `banned_at`, `banned_by_admin_id`, `ban_reason`.
- У админа дополнительно есть отдельный boolean-флаг `is_active`. Он не заменяет `account_status`, а дополняет его: `is_active` управляет включённостью админского доступа, `account_status` — общей блокировкой аккаунта.

---

## 2. `Admin`: `AdminRole`, `AdminActionType`, `AdminEntityType`

### 2.1. Роли сотрудников: `AdminRole`

| Роль | Значение в БД | Смысл |
|---|---:|---|
| `OWNER` | `owner` | Владелец системы, полный доступ. |
| `ADMIN` | `admin` | Админ: управление каталогом, заявками, настройками. |
| `MANAGER` | `manager` | Менеджер: обработка заявок и поддержка. Значение по умолчанию для новых админов. |

`Admin.role` хранится как `SAEnum(AdminRole, name="admin_role")`.

### 2.2. Типы действий администратора: `AdminActionType`

`AdminActionType` — это не статус сущности, а enum для audit-журнала `AdminAction.action_type`. В БД поле `action_type` хранится строкой (`String(64)`), поэтому enum нужен как кодовый whitelist/словарь допустимых действий.

| Action type | Значение | Для чего |
|---|---:|---|
| `CREATE_ITEM` | `create_item` | Создание товара каталога. |
| `UPDATE_ITEM` | `update_item` | Обновление товара каталога. |
| `HIDE_ITEM` | `hide_item` | Скрытие товара. |
| `ARCHIVE_ITEM` | `archive_item` | Архивация товара. |
| `TAKE_RENTAL_IN_PROGRESS` | `take_rental_in_progress` | Взять заявку в обработку. |
| `CONFIRM_RENTAL` | `confirm_rental` | Подтвердить заявку. |
| `REJECT_RENTAL` | `reject_rental` | Отклонить заявку. |
| `CANCEL_RENTAL` | `cancel_rental` | Отменить заявку. |
| `COMPLETE_RENTAL` | `complete_rental` | Завершить заявку. |
| `ADMIN_CANCEL_RENTAL` | `admin_cancel_rental` | Административная отмена заявки. |
| `CLOSE_SUPPORT_TICKET` | `close_support_ticket` | Закрыть обращение в поддержку. |
| `BAN_USER` | `ban_user` | Заблокировать пользователя. |
| `UNBAN_USER` | `unban_user` | Разблокировать пользователя. |

### 2.3. Типы сущностей audit-журнала: `AdminEntityType`

`AdminEntityType` — enum для `AdminAction.entity_type`.

| Entity type | Значение | Сущность |
|---|---:|---|
| `RENTAL` | `rental` | Заявка на аренду. |
| `ITEM` | `item` | Товар каталога. |
| `USER` | `user` | Клиент. |
| `ADMIN` | `admin` | Админ/сотрудник. |
| `SUPPORT_TICKET` | `support_ticket` | Обращение в поддержку. |

### Важное отличие от старой документации

В старом `docs_admin_status.md` были идеи `CANCEL_STATUS_MAP`, `ALLOWED_TARGETS`, `TERMINAL_STATUSES` для dispute/аренд. В актуальном коде этого слоя нет:

- `TERMINAL_STATUSES` находится в `status/rental_status.py`.
- `CANCEL_STATUS_MAP` и `ALLOWED_TARGETS` сейчас не реализованы как рабочие структуры.
- Спор (`DISPUTED`) в актуальном `RentalStatus` не используется.

---

## 3. `Item`: `ItemStatus`

Текущий lifecycle товара — это lifecycle корпоративного каталога: товар может быть черновиком, опубликованным, временно скрытым или окончательно архивированным.

| Статус | Значение в БД | Смысл | Видимость клиенту | Можно создать новую заявку? |
|---|---:|---|---|---|
| `DRAFT` | `DRAFT` | Товар создан, но ещё не опубликован. | Нет | Нет |
| `ACTIVE` | `ACTIVE` | Товар виден клиентам в каталоге. | Да | Да |
| `HIDDEN` | `HIDDEN` | Товар временно скрыт, но может быть возвращён в каталог. | Нет | Нет |
| `ARCHIVED` | `ARCHIVED` | Товар окончательно снят с каталога, исторически сохранён. | Нет | Нет |

`Item.status` хранится как `SAEnum(ItemStatus, name="item_status")`, значение по умолчанию — `ItemStatus.DRAFT`.

### Разрешённые переходы

```text
DRAFT  -> ACTIVE
DRAFT  -> HIDDEN
DRAFT  -> ARCHIVED

ACTIVE -> HIDDEN
ACTIVE -> ARCHIVED

HIDDEN -> ACTIVE
HIDDEN -> ARCHIVED

ARCHIVED -> нет переходов
```

Таблица переходов реализована через `ALLOWED_STATUS_TRANSITIONS`, проверка — через `can_transition(old_status, new_status)`.

### Бизнес-смысл переходов

- `DRAFT -> ACTIVE` — товар подготовили и опубликовали.
- `DRAFT -> HIDDEN` — товар создали, но решили пока не показывать.
- `DRAFT -> ARCHIVED` — товар создали ошибочно или решили не использовать.
- `ACTIVE -> HIDDEN` — временно убрали из каталога.
- `ACTIVE -> ARCHIVED` — окончательно сняли из каталога.
- `HIDDEN -> ACTIVE` — вернули в каталог.
- `HIDDEN -> ARCHIVED` — окончательно убрали скрытый товар.
- `ARCHIVED` — финальное состояние товара.

### Связь с заявками

Для каталога критично правило: публичные выборки используют только `ACTIVE`-товары. Репозиторий `ItemRepository` применяет фильтр `Item.status == ItemStatus.ACTIVE` при `active_only=True`.

Перед скрытием товара бизнес-слой должен учитывать открытые заявки по этому товару. Проверка открытых заявок опирается на `RentalRepository.has_open_rentals_for_item(...)` и `open_statuses()` из rental-статусов.

---

## 4. `Rental`: `RentalStatus`

Текущий `RentalStatus` описывает не «сделку между владельцем и арендатором», а клиентскую заявку на аренду товара компании.

| Статус | Значение в БД | Смысл | Класс |
|---|---:|---|---|
| `REQUESTED` | `requested` | Клиент отправил новую заявку; менеджер ещё не взял её в работу. | Open |
| `IN_PROGRESS` | `in_progress` | Заявка в обработке; менеджер смотрит наличие, связывается с клиентом, уточняет условия. | Open |
| `CONFIRMED` | `confirmed` | Заявка подтверждена менеджером; условия согласованы, товар зарезервирован/готовится к выдаче. | Open |
| `REJECTED` | `rejected` | Заявка отклонена менеджером: товар недоступен, условия невозможны и т.п. | Terminal |
| `COMPLETED` | `completed` | Заявка завершена: аренда отработана, товар возвращён/услуга закрыта. | Terminal |
| `CANCELLED_BY_CLIENT` | `cancelled_by_client` | Заявка отменена клиентом. | Terminal |
| `CANCELLED_BY_ADMIN` | `cancelled_by_admin` | Заявка отменена менеджером/админом: клиент не отвечает, дубль, условия не согласованы и т.п. | Terminal |

`Rental.status` хранится как `SAEnum(RentalStatus, name="rental_status")`, значение по умолчанию — `RentalStatus.REQUESTED`.

### Open-статусы

Open-статусы означают, что заявка ещё жива и потенциально блокирует товар/количество товара:

```text
REQUESTED
IN_PROGRESS
CONFIRMED
```

В коде они собраны в `OPEN_STATUSES` и доступны через `open_statuses()` для SQL-фильтров вида `Rental.status.in_(open_statuses())`.

### Terminal-статусы

Terminal-статусы означают, что заявка закрыта и больше не находится в работе:

```text
REJECTED
CANCELLED_BY_CLIENT
CANCELLED_BY_ADMIN
COMPLETED
```

В коде они собраны в `TERMINAL_STATUSES`; проверка выполняется через `is_terminal_status(status)`.

### Разрешённые переходы

```text
REQUESTED -> IN_PROGRESS
REQUESTED -> CONFIRMED
REQUESTED -> REJECTED
REQUESTED -> CANCELLED_BY_CLIENT
REQUESTED -> CANCELLED_BY_ADMIN

IN_PROGRESS -> CONFIRMED
IN_PROGRESS -> REJECTED
IN_PROGRESS -> CANCELLED_BY_CLIENT
IN_PROGRESS -> CANCELLED_BY_ADMIN

CONFIRMED -> COMPLETED
CONFIRMED -> CANCELLED_BY_CLIENT
CONFIRMED -> CANCELLED_BY_ADMIN

REJECTED -> нет переходов
CANCELLED_BY_CLIENT -> нет переходов
CANCELLED_BY_ADMIN -> нет переходов
COMPLETED -> нет переходов
```

Переходы описаны в `ALLOWED_STATUS_TRANSITIONS`, проверка — через `can_transition(old_status, new_status)`.

### UI-лейблы

В `STATUS_LABELS` сейчас заданы такие человеко-читаемые подписи:

| Статус | Лейбл |
|---|---|
| `REQUESTED` | `Заявка отправлена` |
| `IN_PROGRESS` | `В обработке` |
| `CONFIRMED` | `Подтверждена` |
| `REJECTED` | `Отклонена` |
| `CANCELLED_BY_CLIENT` | `Отменена клиентом` |
| `CANCELLED_BY_ADMIN` | `Отменена менеджером` |
| `COMPLETED` | `Завершена` |

### Бизнес-сценарий

1. Клиент создаёт заявку — она получает `REQUESTED`.
2. Менеджер может взять заявку в работу — `REQUESTED -> IN_PROGRESS`.
3. Менеджер может подтвердить заявку — `REQUESTED/IN_PROGRESS -> CONFIRMED`.
4. Менеджер может отклонить заявку — `REQUESTED/IN_PROGRESS -> REJECTED`.
5. Клиент может отказаться от заявки, пока она не закрыта — `REQUESTED/IN_PROGRESS/CONFIRMED -> CANCELLED_BY_CLIENT`.
6. Админ/менеджер может отменить заявку — `REQUESTED/IN_PROGRESS/CONFIRMED -> CANCELLED_BY_ADMIN`.
7. Подтверждённая заявка после выполнения закрывается — `CONFIRMED -> COMPLETED`.

---

## 5. `Review`: `ReviewStatus`

Отзывы проходят отдельную модерацию. Клиентский отзыв сначала создаётся как ожидающий проверки, затем админ/менеджер решает, публиковать его или нет.

| Статус | Значение в БД | Смысл | Публично виден? |
|---|---:|---|---|
| `PENDING` | `pending` | Отзыв создан клиентом и ожидает проверки. | Нет |
| `PUBLISHED` | `published` | Отзыв прошёл проверку и может отображаться публично. | Да |
| `HIDDEN` | `hidden` | Отзыв временно скрыт из публичного отображения. | Нет |
| `REJECTED` | `rejected` | Отзыв отклонён и не должен публиковаться. | Нет |

`Review.status` хранится как `SAEnum(ReviewStatus, name="review_status")`, значение по умолчанию — `ReviewStatus.PENDING`.

### Разрешённые переходы

```text
PENDING -> PUBLISHED
PENDING -> REJECTED

PUBLISHED -> HIDDEN

HIDDEN -> PUBLISHED
HIDDEN -> REJECTED

REJECTED -> PENDING
```

### Бизнес-смысл

- `PENDING` — новое состояние после создания отзыва.
- `PUBLISHED` — единственный статус, который должен участвовать в публичных списках и расчёте публичной статистики.
- `HIDDEN` — временное снятие уже опубликованного отзыва.
- `REJECTED` — отказ в публикации.
- Возврат `REJECTED -> PENDING` позволяет переотправить/пересмотреть отзыв после корректировок или ошибочного решения.

Репозиторий отзывов поддерживает фильтрацию по статусу и по умолчанию считает статистику товара только по `PUBLISHED`-отзывам.

---

## 6. `SupportTicket`: `SupportTicketStatus`

У поддержки минимальный lifecycle: обращение либо открыто, либо закрыто.

| Статус | Значение в БД | Смысл | Класс |
|---|---:|---|---|
| `OPEN` | `open` | Обращение открыто и ждёт ответа/обработки менеджером. | Open |
| `CLOSED` | `closed` | Обращение закрыто менеджером; вопрос решён или не требует действий. | Terminal |

`SupportTicket.status` хранится как `SAEnum(SupportTicketStatus, name="support_ticket_status")`, значение по умолчанию — `SupportTicketStatus.OPEN`.

### Разрешённые переходы

```text
OPEN -> CLOSED
CLOSED -> нет переходов
```

Отдельной таблицы `ALLOWED_STATUS_TRANSITIONS` сейчас нет. 
Закрытие реализуется атомарно в репозитории: обновляется только тикет в статусе `OPEN`, при этом выставляются `status=CLOSED`, `closed_at`, `closed_by_admin_id`.

### Инварианты

В модели есть ограничение консистентности закрытия:

```text
closed_at IS NULL AND closed_by_admin_id IS NULL
OR
closed_at IS NOT NULL AND closed_by_admin_id IS NOT NULL
```

То есть нельзя получить тикет, у которого есть дата закрытия без админа, или админ закрытия без даты закрытия.

---

## 7. Сводная таблица по всем status-enum

| Сущность | Enum | Начальный/default статус | Open/рабочие статусы | Terminal/закрытые статусы |
|---|---|---|---|---|
| User/Admin account | `AccountStatus` | `ACTIVE` | `ACTIVE`, `BANNED` как переключаемые состояния доступа | Нет финального статуса |
| Item | `ItemStatus` | `DRAFT` | `DRAFT`, `ACTIVE`, `HIDDEN` | `ARCHIVED` |
| Rental | `RentalStatus` | `REQUESTED` | `REQUESTED`, `IN_PROGRESS`, `CONFIRMED` | `REJECTED`, `CANCELLED_BY_CLIENT`, `CANCELLED_BY_ADMIN`, `COMPLETED` |
| Review | `ReviewStatus` | `PENDING` | `PENDING`, `PUBLISHED`, `HIDDEN`, `REJECTED` как moderation-состояния | Нет окончательного terminal: `REJECTED` можно вернуть в `PENDING` |
| SupportTicket | `SupportTicketStatus` | `OPEN` | `OPEN` | `CLOSED` |
| Admin | `AdminRole` | `MANAGER` | `OWNER`, `ADMIN`, `MANAGER` | Не статус жизненного цикла |
| AdminAction | `AdminActionType` / `AdminEntityType` | Нет | Audit-классификаторы | Не статусы жизненного цикла |

---

## 8. Практические правила для разработки

1. **Не добавлять строковые статусы прямо в коде.** Новый статус сначала добавляется в соответствующий enum в `status/*.py`.
2. **Не менять статус без проверки переходов**, если для enum есть `ALLOWED_STATUS_TRANSITIONS` и `can_transition(...)`.
3. **Для публичного каталога использовать только `ItemStatus.ACTIVE`.** `DRAFT`, `HIDDEN`, `ARCHIVED` не должны попадать в клиентскую выдачу.
4. **Для блокировки товара заявками использовать `open_statuses()`.** Сейчас товар блокируют `REQUESTED`, `IN_PROGRESS`, `CONFIRMED`.
5. **Для закрытых заявок использовать `is_terminal_status(...)`.** Сейчас закрытые: `REJECTED`, `CANCELLED_BY_CLIENT`, `CANCELLED_BY_ADMIN`, `COMPLETED`.
6. **Отзывы публично показывать только в `ReviewStatus.PUBLISHED`.** Остальные статусы — модерационные/непубличные.
7. **Support ticket закрывать только из `OPEN` в `CLOSED`.** При закрытии обязательно выставлять `closed_at` и `closed_by_admin_id` вместе.
8. **AdminAction — это audit, а не состояние бизнес-сущности.** Не путать `AdminActionType.CANCEL_RENTAL` с `RentalStatus.CANCELLED_BY_ADMIN`: первое — запись действия, второе — состояние заявки.
