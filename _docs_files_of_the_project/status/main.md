# Единая документация по статусам проекта

Документ описывает актуальные статусы проекта и то, как они используются в моделях, схемах, репозиториях, сервисах и UI.

Текущий проект — Telegram-бот компании по аренде товаров:
- компания ведёт каталог товаров;
- клиент выбирает товар и создаёт заявку на аренду;
- менеджер/админ обрабатывает заявку;
- клиент может оставить отзыв после завершения заявки;
- поддержка ведётся через тикеты;
- действия сотрудников пишутся в audit-журнал.

---

## 0. Карта файлов `status/*.py`

| Файл | Что описывает | Где используется |
|---|---|---|
| `status/user_status.py` | `AccountStatus`, переходы аккаунта | `User.account_status`, `Admin.account_status`, middleware доступа, `UserService` |
| `status/admin_status.py` | `AdminRole`, `AdminActionType`, `AdminEntityType`, audit-map для заявок | `Admin.role`, `AdminAction`, админские сервисы |
| `status/item_status.py` | `ItemStatus`, lifecycle товара каталога | `Item.status`, каталог, админка товаров, проверки заявок |
| `status/rental_status.py` | `RentalStatus`, open/terminal-классификация, timestamp-поля, UI-labels | `Rental.status`, заявки, уведомления, админка, проверки доступности товара |
| `status/review_status.py` | `ReviewStatus`, moderation lifecycle отзыва | `Review.status`, публичные отзывы, статистика товара |
| `status/support_ticket_status.py` | `SupportTicketStatus` | `SupportTicket.status`, поддержка, админка тикетов |

Главное правило слоя: строки статусов не должны размазываться по проекту. Если нужен новый статус — сначала добавляем enum/переходы в `status/*.py`, затем уже используем его в моделях, схемах, сервисах и UI.

---

## 1. Аккаунты: `AccountStatus`

`AccountStatus` — общий статус доступа для клиентов и сотрудников компании.

Он используется в двух моделях:
- `User.account_status` — доступ клиента к боту;
- `Admin.account_status` — общая блокировка сотрудника.

У `Admin` дополнительно есть `is_active`: это отдельный флаг включённости админского доступа. Он не заменяет `account_status`.

### Enum

| Статус | Значение | Смысл | Terminal? |
|---|---|---|---|
| `ACTIVE` | `ACTIVE` | Аккаунт активен; пользователь/сотрудник может пользоваться разрешёнными функциями. | Нет |
| `BANNED` | `BANNED` | Доступ заблокирован администратором. | Нет, потому что можно вернуть в `ACTIVE` |

### Переходы

```text
ACTIVE -> BANNED
BANNED -> ACTIVE
```

В коде:
- `ALLOWED_STATUS_TRANSITIONS: dict[AccountStatus, frozenset[AccountStatus]]`;
- `can_transition(old_status, new_status) -> bool`.

### Практический смысл

- Бан/разбан клиента выполняет `UserService` через `can_transition(...)`.
- При бане клиента используются audit-поля модели `User`: `banned_at`, `banned_by_admin_id`, `ban_reason`.
- Middleware и callback-фильтры проверяют, что обычный клиент не находится в `BANNED`.
- У сотрудника доступ зависит от двух вещей: `account_status == ACTIVE` и `is_active == True`.

---

## 2. Админский контур

В админском контуре есть три enum-типа:
- `AdminRole` — роль сотрудника;
- `AdminActionType` — тип audit-действия;
- `AdminEntityType` — тип сущности, к которой относится audit-запись.

Важно: `AdminActionType` и `AdminEntityType` — это не lifecycle-статусы бизнес-сущностей. Это классификаторы журнала действий администратора.

---

## 2.1. Роли сотрудников: `AdminRole`

`AdminRole` хранится в `Admin.role` как `SAEnum(AdminRole, name="admin_role")`.

| Роль | Значение | Смысл |
|---|---|---|
| `OWNER` | `owner` | Владелец системы, полный доступ. |
| `ADMIN` | `admin` | Администратор: управление каталогом, заявками, настройками. |
| `MANAGER` | `manager` | Менеджер: обработка заявок и поддержки. Значение по умолчанию для новых сотрудников. |

### Что важно

- Для `AdminRole` нет `ALLOWED_STATUS_TRANSITIONS`: роль меняется как поле сотрудника, а не как workflow.
- Доступ к конкретным действиям должен проверяться в сервисах/handlers, а не самим enum.
- По умолчанию в `AdminCreate` и модели используется `MANAGER`.

---

## 2.2. Типы действий администратора: `AdminActionType`

`AdminActionType` используется для `AdminAction.action_type`. В модели поле хранится как строка (`String(64)`), а enum нужен как whitelist/словарь допустимых действий.

| Action type | Значение | Когда писать |
|---|---|---|
| `CREATE_ITEM` | `create_item` | Создание товара каталога. |
| `UPDATE_ITEM` | `update_item` | Обновление товара каталога. |
| `HIDE_ITEM` | `hide_item` | Скрытие товара из каталога. |
| `ARCHIVE_ITEM` | `archive_item` | Архивация товара. |
| `TAKE_RENTAL_IN_PROGRESS` | `take_rental_in_progress` | Менеджер взял заявку в обработку. |
| `CONFIRM_RENTAL` | `confirm_rental` | Менеджер подтвердил заявку. |
| `REJECT_RENTAL` | `reject_rental` | Менеджер отклонил заявку. |
| `CANCEL_RENTAL` | `cancel_rental` | Общая fallback-запись отмены заявки. |
| `COMPLETE_RENTAL` | `complete_rental` | Менеджер завершил заявку. |
| `ADMIN_CANCEL_RENTAL` | `admin_cancel_rental` | Компания/админ отменили подтверждённую заявку. |
| `CLOSE_SUPPORT_TICKET` | `close_support_ticket` | Сотрудник закрыл тикет поддержки. |
| `BAN_USER` | `ban_user` | Пользователь заблокирован. |
| `UNBAN_USER` | `unban_user` | Пользователь разблокирован. |

### Mapping статуса заявки в audit-действие

В `status/admin_status.py` есть `RENTAL_STATUS_ADMIN_ACTIONS`:

| Новый `RentalStatus` | Audit-действие |
|---|---|
| `IN_PROGRESS` | `TAKE_RENTAL_IN_PROGRESS` |
| `CONFIRMED` | `CONFIRM_RENTAL` |
| `REJECTED` | `REJECT_RENTAL` |
| `CANCELLED_BY_ADMIN` | `ADMIN_CANCEL_RENTAL` |
| `COMPLETED` | `COMPLETE_RENTAL` |

`admin_action_for_rental_status(status)` возвращает значение из этой таблицы, а для статуса вне таблицы — fallback `AdminActionType.CANCEL_RENTAL`.

Это важно для клиентской отмены: `RentalStatus.CANCELLED_BY_CLIENT` не является админским целевым статусом, поэтому при ручном использовании helper вернёт общий `CANCEL_RENTAL`.

---

## 2.3. Типы сущностей audit-журнала: `AdminEntityType`

`AdminEntityType` используется для `AdminAction.entity_type`.

| Entity type | Значение | Сущность |
|---|---|---|
| `RENTAL` | `rental` | Заявка на аренду. |
| `ITEM` | `item` | Товар каталога. |
| `USER` | `user` | Клиент. |
| `ADMIN` | `admin` | Сотрудник/админ. |
| `SUPPORT_TICKET` | `support_ticket` | Обращение в поддержку. |

### Что важно

- `AdminAction.entity_id` хранится строкой, потому что audit-журнал универсальный.
- `AdminAction.admin_id` может стать `NULL` при удалении сотрудника, но `admin_tg_id` остаётся обязательным.
- `AdminAction` не меняет состояние сущности. Он только фиксирует факт действия.

---

## 3. Каталог товаров: `ItemStatus`

`ItemStatus` описывает lifecycle карточки товара каталога компании.

Это не статус пользовательского объявления и не модерация объявления владельца. Товар создаёт/редактирует сотрудник компании, а клиент видит только опубликованные товары.

`Item.status` хранится как `SAEnum(ItemStatus, name="item_status")`, default — `ItemStatus.DRAFT`.

### Enum

| Статус | Значение | Смысл | Видимость клиенту | Можно создать новую заявку? |
|---|---|---|---|---|
| `DRAFT` | `DRAFT` | Товар создан, но ещё не опубликован. | Нет | Нет |
| `ACTIVE` | `ACTIVE` | Товар виден клиентам в каталоге. | Да | Да |
| `HIDDEN` | `HIDDEN` | Товар временно скрыт, но может быть возвращён. | Нет | Нет |
| `ARCHIVED` | `ARCHIVED` | Товар больше не используется, исторически сохранён. | Нет | Нет |

### Переходы

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

В коде:
- `ALLOWED_STATUS_TRANSITIONS: dict[ItemStatus, frozenset[ItemStatus]]`;
- `can_transition(old_status, new_status) -> bool`.

### Бизнес-смысл переходов

- `DRAFT -> ACTIVE` — товар подготовили и опубликовали.
- `DRAFT -> HIDDEN` — товар создали, но пока не показывают.
- `DRAFT -> ARCHIVED` — товар создали ошибочно или решили не использовать.
- `ACTIVE -> HIDDEN` — временно убрать из клиентского каталога.
- `ACTIVE -> ARCHIVED` — окончательно снять с каталога.
- `HIDDEN -> ACTIVE` — вернуть товар в каталог.
- `HIDDEN -> ARCHIVED` — окончательно убрать скрытый товар.
- `ARCHIVED` — финальное состояние: переходов назад нет.

### Связь с заявками

Публичные выборки товаров должны использовать только `ItemStatus.ACTIVE`. В репозитории это фильтр `Item.status == ItemStatus.ACTIVE` при `active_only=True`.

Перед переводом товара в `HIDDEN` или `ARCHIVED` сервис товаров проверяет открытые заявки:
- `RentalRepository.has_open_rentals_for_item(item_id)`;
- `open_statuses()` из `status/rental_status.py`.

То есть статус товара нельзя рассматривать отдельно от заявок: скрытие/архивация товара с открытыми заявками может нарушить бизнес-процесс.

---

## 4. Заявки на аренду: `RentalStatus`

`RentalStatus` описывает lifecycle клиентской заявки на аренду товара компании.

Это не старая модель сделки `owner/renter`. В актуальном проекте:
- клиент = `Rental.user_id`;
- товар = `Rental.item_id`;
- назначенный менеджер = `Rental.assigned_admin_id`;
- менеджер/админ обрабатывает заявку от имени компании.

`Rental.status` хранится как `SAEnum(RentalStatus, name="rental_status")`, default — `RentalStatus.REQUESTED`.

### Enum

| Статус | Значение | Смысл | Класс |
|---|---|---|---|
| `REQUESTED` | `requested` | Новая заявка от клиента; менеджер ещё не взял её в работу. | Open |
| `IN_PROGRESS` | `in_progress` | Заявка в обработке; менеджер смотрит наличие и связывается с клиентом. | Open |
| `CONFIRMED` | `confirmed` | Заявка подтверждена; условия согласованы, товар зарезервирован/готовится к выдаче. | Open |
| `REJECTED` | `rejected` | Заявка отклонена менеджером до подтверждения. | Terminal |
| `COMPLETED` | `completed` | Заявка завершена: аренда отработана, товар возвращён/услуга закрыта. | Terminal |
| `CANCELLED_BY_CLIENT` | `cancelled_by_client` | Клиент отменил заявку. | Terminal |
| `CANCELLED_BY_ADMIN` | `cancelled_by_admin` | Компания/админ отменили уже подтверждённую заявку. | Terminal |

В коде закомментированы старые идеи `ACTIVE` и `DISPUTED`; в текущем lifecycle они не используются.

---

## 4.1. Open и Terminal

### Open-статусы

Open-статусы означают, что заявка ещё находится в работе и влияет на доступность товара.

```text
REQUESTED
IN_PROGRESS
CONFIRMED
```

В коде:
- `OPEN_STATUSES`;
- `is_open_status(status) -> bool`;
- `open_statuses() -> tuple[RentalStatus, ...]` для SQL `IN`.

Используется в проверках доступности товара и в `RentalRepository.has_open_rentals_for_item(...)`.

### Terminal-статусы

Terminal-статусы означают, что заявка закрыта и не должна двигаться дальше.

```text
REJECTED
CANCELLED_BY_CLIENT
CANCELLED_BY_ADMIN
COMPLETED
```

В коде:
- `TERMINAL_STATUSES`;
- `is_terminal_status(status) -> bool`.



```
TERMINAL_STATUSES нужен для проверок:
    можно ли ещё менять заявку?
    показывать ли заявку как активную?
    считать ли товар занятым?
    можно ли отменить заявку?


OPEN_STATUSES нужен в:
    has_open_rentals_for_item()
    ensure_item_available()
    list_recent_open_by_item_id()
    open_statuses() для SQL .in_(...)
```

---

## 4.2. Переходы `RentalStatus`

Актуальные переходы строго такие, как в `ALLOWED_STATUS_TRANSITIONS`:

```text
REQUESTED -> IN_PROGRESS
REQUESTED -> CONFIRMED
REQUESTED -> REJECTED
REQUESTED -> CANCELLED_BY_CLIENT

IN_PROGRESS -> CONFIRMED
IN_PROGRESS -> REJECTED
IN_PROGRESS -> CANCELLED_BY_CLIENT

CONFIRMED -> COMPLETED
CONFIRMED -> CANCELLED_BY_CLIENT
CONFIRMED -> CANCELLED_BY_ADMIN

REJECTED -> нет переходов
CANCELLED_BY_CLIENT -> нет переходов
CANCELLED_BY_ADMIN -> нет переходов
COMPLETED -> нет переходов
```

Важное отличие:
- `CANCELLED_BY_ADMIN` разрешён только из `CONFIRMED`.
- До подтверждения менеджер не «отменяет» заявку, а отклоняет её через `REJECTED`.
- Поэтому `REQUESTED -> CANCELLED_BY_ADMIN` и `IN_PROGRESS -> CANCELLED_BY_ADMIN` в текущем коде не разрешены.

Проверка переходов: `can_transition(old_status, new_status)`.

---

## 4.3. Timestamp-поля статусов

`STATUS_TIMESTAMP_FIELDS` связывает статус с датами, которые нужно проставить при переходе.

| Новый статус | Timestamp-поля |
|---|---|
| `IN_PROGRESS` | `in_progress_at` |
| `CONFIRMED` | `confirmed_at` |
| `REJECTED` | `rejected_at`, `closed_at` |
| `CANCELLED_BY_CLIENT` | `cancelled_at`, `closed_at` |
| `CANCELLED_BY_ADMIN` | `cancelled_at`, `closed_at` |
| `COMPLETED` | `completed_at`, `closed_at` |

`REQUESTED` не имеет отдельного status timestamp: дата создания заявки уже хранится в `created_at`.

В репозитории `RentalRepository._build_status_update(...)` берёт поля через `status_timestamp_fields(status)` и проставляет `datetime.now(timezone.utc)`.

---

## 4.4. UI-лейблы заявок

`STATUS_LABELS` используется в уведомлениях и UI.

| Статус | Лейбл |
|---|---|
| `REQUESTED` | `Заявка отправлена` |
| `IN_PROGRESS` | `В обработке` |
| `CONFIRMED` | `Подтверждена` |
| `REJECTED` | `Отклонена` |
| `CANCELLED_BY_CLIENT` | `Отменена клиентом` |
| `CANCELLED_BY_ADMIN` | `Отменена компанией` |
| `COMPLETED` | `Завершена` |

Если лейбл не найден, UI обычно может fallback-нуться на `status.value`.

---

## 4.5. Бизнес-сценарий заявки

1. Клиент создаёт заявку — статус `REQUESTED`.
2. Менеджер берёт заявку в работу — `REQUESTED -> IN_PROGRESS`.
3. Менеджер может подтвердить заявку — `REQUESTED/IN_PROGRESS -> CONFIRMED`.
4. Пока заявка не подтверждена, менеджер может её отклонить — `REQUESTED/IN_PROGRESS -> REJECTED`.
5. Клиент может отменить заявку до закрытия — `REQUESTED/IN_PROGRESS/CONFIRMED -> CANCELLED_BY_CLIENT`.
6. Компания может отменить подтверждённую заявку — `CONFIRMED -> CANCELLED_BY_ADMIN`.
7. После выполнения подтверждённая заявка закрывается — `CONFIRMED -> COMPLETED`.

### Где проверяется

- `RentalService` проверяет клиентские переходы через `can_transition(...)`.
- `AdminRentalService` проверяет админские переходы через `can_transition(...)` и пишет audit-действие.
- `RentalRepository.try_update_status(...)` и `try_update_status_if_user(...)` делают атомарный SQL `UPDATE`, где одновременно проверяется текущий `expected_status`.

---

## 5. Отзывы: `ReviewStatus`

`ReviewStatus` описывает moderation lifecycle отзыва клиента.

Отзыв привязан к заявке (`rental_id`), пользователю (`user_id`) и опционально к товару (`item_id`). Оставлять отзыв по бизнес-логике можно после завершения заявки (`RentalStatus.COMPLETED`).

`Review.status` хранится как `SAEnum(ReviewStatus, name="review_status")`, default — `ReviewStatus.PENDING`.

### Enum

| Статус | Значение | Смысл | Публично виден? |
|---|---|---|---|
| `PENDING` | `pending` | Отзыв создан клиентом и ожидает проверки менеджером/админом. | Нет |
| `PUBLISHED` | `published` | Отзыв прошёл проверку и может отображаться публично. | Да |
| `HIDDEN` | `hidden` | Опубликованный отзыв временно скрыт. | Нет |
| `REJECTED` | `rejected` | Отзыв отклонён и не должен публиковаться. | Нет |

### Переходы

```text
PENDING -> PUBLISHED
PENDING -> REJECTED

PUBLISHED -> HIDDEN

HIDDEN -> PUBLISHED
HIDDEN -> REJECTED

REJECTED -> PENDING
```

В коде есть `ALLOWED_STATUS_TRANSITIONS`, но отдельной функции `can_transition(...)` для отзывов сейчас нет. Если сервис начнёт активно менять статусы отзывов, лучше добавить helper по аналогии с товарами/заявками/аккаунтами.

### Практический смысл

- `PUBLISHED` — единственный статус, который должен попадать в публичные списки и публичную статистику.
- `ReviewRepository.list_by_item_id(...)` по умолчанию отдаёт только `PUBLISHED`.
- `ReviewRepository.get_stats_for_item(...)` по умолчанию считает рейтинг только по `PUBLISHED`.
- `HIDDEN` нужен для временного снятия отзыва без удаления.
- `REJECTED -> PENDING` позволяет вернуть отзыв на повторную модерацию.

---

## 6. Поддержка: `SupportTicketStatus`

`SupportTicketStatus` описывает минимальный lifecycle обращения клиента в поддержку.

Тикет может быть связан:
- с клиентом через `user_id`;
- с товаром через `item_id`;
- с заявкой через `rental_id`.

`SupportTicket.status` хранится как `SAEnum(SupportTicketStatus, name="support_ticket_status")`, default — `SupportTicketStatus.OPEN`.

### Enum

| Статус | Значение | Смысл | Класс |
|---|---|---|---|
| `OPEN` | `open` | Обращение открыто и ждёт ответа/обработки менеджером. | Open |
| `CLOSED` | `closed` | Обращение закрыто менеджером; вопрос решён или больше не требует действий. | Terminal |

### Переходы

```text
OPEN -> CLOSED
CLOSED -> нет переходов
```

Отдельной таблицы `ALLOWED_STATUS_TRANSITIONS` сейчас нет. Закрытие реализовано технически в `SupportTicketRepository.close(...)`:
- обновляется только тикет со статусом `OPEN`;
- выставляется `status=CLOSED`;
- выставляются `closed_at` и `closed_by_admin_id`.

### Инварианты модели

В модели есть check constraint:

```text
closed_at IS NULL AND closed_by_admin_id IS NULL
OR
closed_at IS NOT NULL AND closed_by_admin_id IS NOT NULL
```

То есть дата закрытия и сотрудник, закрывший тикет, должны быть заполнены вместе или оба отсутствовать.

`touch_admin_reply(...)` обновляет `admin_last_reply_at` и не является сменой статуса.

---

## 7. Сводная таблица статусов

| Область | Enum | Default / старт | Рабочие состояния | Закрытые / финальные состояния | Есть `can_transition`? |
|---|---|---|---|---|---|
| Аккаунт клиента/админа | `AccountStatus` | `ACTIVE` | `ACTIVE`, `BANNED` как переключаемые состояния доступа | Нет финального статуса | Да |
| Роль сотрудника | `AdminRole` | `MANAGER` | `OWNER`, `ADMIN`, `MANAGER` | Не lifecycle | Нет |
| Audit-действие | `AdminActionType` | Нет | Классификаторы действий | Не lifecycle | Нет |
| Audit-сущность | `AdminEntityType` | Нет | Классификаторы сущностей | Не lifecycle | Нет |
| Товар | `ItemStatus` | `DRAFT` | `DRAFT`, `ACTIVE`, `HIDDEN` | `ARCHIVED` | Да |
| Заявка | `RentalStatus` | `REQUESTED` | `REQUESTED`, `IN_PROGRESS`, `CONFIRMED` | `REJECTED`, `CANCELLED_BY_CLIENT`, `CANCELLED_BY_ADMIN`, `COMPLETED` | Да |
| Отзыв | `ReviewStatus` | `PENDING` | `PENDING`, `PUBLISHED`, `HIDDEN`, `REJECTED` как moderation-состояния | Нет абсолютного terminal: `REJECTED` можно вернуть в `PENDING` | Нет отдельной функции |
| Поддержка | `SupportTicketStatus` | `OPEN` | `OPEN` | `CLOSED` | Нет |

---

## 8. Что осталось из старых идей и сейчас не используется

В старых документах были статусы и роли, которые относились к marketplace-модели `owner/renter`:
- `RentalActorRole`;
- `ACTIVE` у аренды;
- `DISPUTED`;
- `REJECTED_BY_OWNER` / `REJECTED_BY_RENTER`;
- `CANCELLED_BY_OWNER` / `CANCELLED_BY_RENTER`;
- `PAYMENT_PENDING`;
- `ADMIN_CANCELLED` как отдельное старое имя;
- `CANCEL_STATUS_MAP`, `ALLOWED_TARGETS` для споров.

В текущем коде этого нет. Актуальная модель проще:
- заявка принадлежит клиенту (`user_id`), а не паре владелец/арендатор;
- компанию представляет менеджер/админ;
- открытые статусы заявки: `REQUESTED`, `IN_PROGRESS`, `CONFIRMED`;
- закрытые статусы: `REJECTED`, `CANCELLED_BY_CLIENT`, `CANCELLED_BY_ADMIN`, `COMPLETED`;
- споры пока не являются отдельным lifecycle-статусом.

---

## 9. Будущие статусы из `future.md`

`_docs_files_of_the_project/status/future.md` фиксирует идеи, которых сейчас нет в коде.

### PaymentStatus

Понадобится при оплатах через Telegram Stars, ЮKassa или другой платёжный провайдер.

Возможные будущие значения:
- `PENDING`;
- `PAID`;
- `FAILED`;
- `REFUNDED`;
- `CANCELLED`.

### DeliveryStatus

Сейчас доставка — это поля заявки:
- `delivery_needed`;
- `delivery_address`.

Отдельный статус доставки понадобится только если доставка станет самостоятельным процессом.

Возможные будущие значения:
- `NOT_REQUIRED`;
- `REQUESTED`;
- `SCHEDULED`;
- `IN_DELIVERY`;
- `DELIVERED`;
- `RETURNED`.

### CartStatus

Понадобится, если появится корзина и сценарий «несколько товаров -> одна заявка».

### NotificationStatus

Понадобится, если проект начнёт логировать отправку уведомлений.

Возможные будущие значения:
- `PENDING`;
- `SENT`;
- `FAILED`;
- `RETRYING`.

---

## 10. Практические правила для разработки

1. **Не писать строковые статусы руками в бизнес-логике.** Использовать enum из `status/*.py`.
2. **Если у enum есть `can_transition(...)`, сервис должен проверять переход до записи в БД.** Сейчас это обязательно для `AccountStatus`, `ItemStatus`, `RentalStatus`.
3. **Публичный каталог = только `ItemStatus.ACTIVE`.** `DRAFT`, `HIDDEN`, `ARCHIVED` не должны попадать клиенту.
4. **Товар с открытыми заявками нельзя бездумно скрывать/архивировать.** Проверять через `open_statuses()` и репозиторий заявок.
5. **До подтверждения заявку админ отклоняет, а не отменяет.** `CANCELLED_BY_ADMIN` разрешён только из `CONFIRMED`.
6. **Закрытые заявки не двигаются дальше.** Проверять через `is_terminal_status(...)`.
7. **Отзывы публично показывать и считать только в `ReviewStatus.PUBLISHED`.** Остальные статусы — модерационные.
8. **Тикет закрывать только из `OPEN` в `CLOSED`.** При закрытии обязательно вместе выставлять `closed_at` и `closed_by_admin_id`.
9. **`AdminActionType` не равен бизнес-статусу.** Например, `ADMIN_CANCEL_RENTAL` — audit-действие, а `RentalStatus.CANCELLED_BY_ADMIN` — состояние заявки.
10. **Новые статусы добавлять вместе с документацией.** При изменении enum нужно обновить этот файл и проверить handlers/services/repositories, где статус используется.


## 11.

>`set()` — изменяемое множество
> 
>`frozenset()` — неизменяемое множество
> 
> далее использую `frozenset()`
