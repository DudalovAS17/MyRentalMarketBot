# AGENT: Status Logic

Файл задаёт правила для слоя `status/` в `MyRentalMarketBot`.

Нужен агентам, которые:
- анализируют enum-статусы проекта;
- добавляют новые lifecycle/status enums;
- правят allowed transitions, terminal/open groups, labels и timestamp fields;
- ревьюят границы `status ↔ service`, `status ↔ model`, `status ↔ handler`.

Главный принцип:

> Status layer описывает **словарь состояний и чистые правила переходов**, но не выполняет **DB-запись**, **Telegram UX** и **business orchestration**.

---

## 1) Scope слоя

`status/` — это lightweight domain constants + pure transition helpers.

Разрешено:
- `enum.Enum` / `StrEnum`;
- sets/groups статусов (`TERMINAL_STATUSES`, `OPEN_STATUSES`);
- maps переходов (`ALLOWED_STATUS_TRANSITIONS`);
- pure helpers вроде `can_transition(...)`, `is_terminal_status(...)`, `status_timestamp_fields(...)`;
- labels для внутреннего отображения статуса, если они стабильны и не содержат UX-сценарий;
- maps для audit/action связи, например `admin_action_for_rental_status(...)`.

Запрещено:
- SQLAlchemy, repositories, sessions, commits;
- Telegram/FSM/UI objects;
- вызовы services;
- user-facing flow logic;
- проверка прав пользователя/админа;
- ownership/participant checks;
- отправка уведомлений;
- side effects.

---

## 2) Текущие status-домены проекта

- `status/item_status.py` — жизненный цикл товара каталога: `DRAFT`, `ACTIVE`, `HIDDEN`, `ARCHIVED`.
- `status/rental_status.py` — жизненный цикл заявки аренды: `REQUESTED`, `IN_PROGRESS`, `CONFIRMED`, terminal statuses.
- `status/user_status.py` — доступ аккаунта: `ACTIVE`, `BANNED`.
- `status/review_status.py` — модерация отзыва: `PENDING`, `PUBLISHED`, `HIDDEN`, `REJECTED`.
- `status/support_ticket_status.py` — состояние обращения: `OPEN`, `CLOSED`.
- `status/admin_status.py` — роли сотрудников, audit action/entity types и map rental status → admin action.

---

## 3) Граница со слоями

### Status → Model

ORM-модель может использовать enum из `status/` через `SAEnum(StatusEnum, name="...")`.

Status layer не должен импортировать ORM-модели.

### Status → Repository

Repository может использовать statuses в фильтрах:
- `Item.status == ItemStatus.ACTIVE`;
- `Rental.status.in_(open_statuses())`.

Status layer не должен знать про SQLAlchemy-запросы.

### Status → Service

Service — главный пользователь transition helpers.

Service должен:
- вызвать `can_transition(old_status, new_status)`;
- решить, что делать при запрете (`ConflictError`, domain error, `False` при `strict=False`);
- записать изменение через repository;
- проставить actor ids, audit, notifications, timestamps через repo/service orchestration.

Status layer не должен сам решать, кто имеет право на переход.

### Status → Handler

Handler может импортировать enum только как тип входного значения/фильтр UI-ветки, если это не тянет business policy в handler.

Handler не должен вручную решать переходы. Он вызывает service.

---

## 4) Каноничный enum + transition map

```python
import enum


class ItemStatus(enum.Enum):
    """Статус товара в каталоге компании."""

    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    HIDDEN = "HIDDEN"
    ARCHIVED = "ARCHIVED"


ALLOWED_STATUS_TRANSITIONS: dict[ItemStatus, frozenset[ItemStatus]] = {
    ItemStatus.DRAFT: frozenset({ItemStatus.ACTIVE, ItemStatus.HIDDEN, ItemStatus.ARCHIVED}),
    ItemStatus.ACTIVE: frozenset({ItemStatus.HIDDEN, ItemStatus.ARCHIVED}),
    ItemStatus.HIDDEN: frozenset({ItemStatus.ACTIVE, ItemStatus.ARCHIVED}),
    ItemStatus.ARCHIVED: frozenset(),
}


def can_transition(old_status: ItemStatus, new_status: ItemStatus) -> bool:
    """Проверить, разрешён ли переход товара из old_status в new_status."""
    return new_status in ALLOWED_STATUS_TRANSITIONS.get(old_status, frozenset())
```

---

## 5) Каноничный lifecycle с группами и timestamps

```python
TERMINAL_STATUSES: frozenset[RentalStatus] = frozenset({
    RentalStatus.REJECTED,
    RentalStatus.CANCELLED_BY_CLIENT,
    RentalStatus.CANCELLED_BY_ADMIN,
    RentalStatus.COMPLETED,
})

OPEN_STATUSES: frozenset[RentalStatus] = frozenset({
    RentalStatus.REQUESTED,
    RentalStatus.IN_PROGRESS,
    RentalStatus.CONFIRMED,
})

STATUS_TIMESTAMP_FIELDS: dict[RentalStatus, tuple[str, ...]] = {
    RentalStatus.IN_PROGRESS: ("in_progress_at",),
    RentalStatus.CONFIRMED: ("confirmed_at",),
    RentalStatus.REJECTED: ("rejected_at", "closed_at"),
    RentalStatus.CANCELLED_BY_CLIENT: ("cancelled_at", "closed_at"),
    RentalStatus.CANCELLED_BY_ADMIN: ("cancelled_at", "closed_at"),
    RentalStatus.COMPLETED: ("completed_at", "closed_at"),
}


def is_terminal_status(status: RentalStatus) -> bool:
    return status in TERMINAL_STATUSES


def is_open_status(status: RentalStatus) -> bool:
    return status in OPEN_STATUSES


def open_statuses() -> tuple[RentalStatus, ...]:
    return tuple(OPEN_STATUSES)


def status_timestamp_fields(status: RentalStatus) -> tuple[str, ...]:
    return STATUS_TIMESTAMP_FIELDS.get(status, ())
```

---

## 6) Naming rules

Enum class:
- `ItemStatus`;
- `RentalStatus`;
- `AccountStatus`;
- `ReviewStatus`;
- `SupportTicketStatus`.

Transition map:
- `ALLOWED_STATUS_TRANSITIONS` внутри конкретного status-файла.

Helpers:
- `can_transition(old_status, new_status)`;
- `is_terminal_status(status)`;
- `is_open_status(status)`;
- `open_statuses()`;
- `status_timestamp_fields(status)`.

Values:
- не менять существующие строковые values без миграции и проверки БД;
- для новых enum values выбрать стиль, уже принятый в конкретном файле (`DRAFT` uppercase для item/user, lowercase для rental/support/review);
- не смешивать DB enum value style внутри одного enum.

---

## 7) Transition rules

Разрешённые переходы должны быть явными.

Хорошо:
- terminal status имеет пустой `frozenset()`;
- open/terminal groups вынесены отдельно;
- impossible transition возвращает `False`, а не кидает исключение в status helper;
- service решает, какое исключение или UX-ветка будет дальше.

Плохо:
- разрешать переход “по умолчанию”;
- делать `return True`, если old_status не найден;
- хранить переходы в handler;
- дублировать transition map в service.

---

## 8) Labels и UX

`STATUS_LABELS` допустимы как стабильные короткие подписи статуса.

Но status layer не должен содержать:
- длинные пользовательские сообщения;
- keyboard labels;
- инструкции пользователю;
- разные тексты под разные Telegram screens.

Если label становится UX-текстом сценария — перенести в `texts/` или handler helper.

---

## 9) Audit/action maps

Связка status → audit action допустима в status/admin layer, если она чистая и стабильная:

```python
RENTAL_STATUS_ADMIN_ACTIONS: dict[RentalStatus, AdminActionType] = {
    RentalStatus.IN_PROGRESS: AdminActionType.TAKE_RENTAL_IN_PROGRESS,
    RentalStatus.CONFIRMED: AdminActionType.CONFIRM_RENTAL,
    RentalStatus.REJECTED: AdminActionType.REJECT_RENTAL,
    RentalStatus.CANCELLED_BY_ADMIN: AdminActionType.ADMIN_CANCEL_RENTAL,
    RentalStatus.COMPLETED: AdminActionType.COMPLETE_RENTAL,
}


def admin_action_for_rental_status(status: RentalStatus) -> AdminActionType:
    return RENTAL_STATUS_ADMIN_ACTIONS.get(status, AdminActionType.CANCEL_RENTAL)
```

Не добавлять сюда запись audit-log в БД. Это делает service/repository.

---

## 10) Checklist

- [ ] Новый enum лежит в `status/`, а не в handler/service.
- [ ] Значения enum не ломают существующие DB values.
- [ ] Переходы описаны через `ALLOWED_STATUS_TRANSITIONS`.
- [ ] Terminal statuses явно имеют пустой набор переходов.
- [ ] Helper functions чистые: без DB, Telegram, service calls и side effects.
- [ ] Service использует `can_transition(...)`, а не дублирует map.
- [ ] Handler не принимает business transition decisions.
- [ ] Labels не превращены в длинные UX-тексты.