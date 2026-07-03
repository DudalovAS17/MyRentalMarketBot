# docs_schemas.md — актуальная объединённая документация по схемам

Документ описывает текущие Pydantic-схемы из папки `schemas/` и их связь с новыми моделями/репозиториями (`db/models/`, `db/repositories/`).

## Общие правила для всех схем

- `Create` — входные данные для создания сущности. Обычно содержит только то, что реально можно передать в слой сервиса/репозитория при создании.
- `Update` — входные данные для изменения сущности. Почти все поля `Optional`, а репозитории применяют `model_dump(exclude_unset=True)`, чтобы отличать «поле не передали» от «передали `None`».
- `Out` — наружный DTO для ответа хендлерам/сервисам. Для ORM-объектов включается `model_config = ConfigDict(from_attributes=True)`.
- `Admin...` — схемы админских действий/модерации. Они отделены от клиентских схем, чтобы не смешивать пользовательский ввод и служебные поля.
- `Internal` — внутренние схемы сервиса: дополняют клиентский ввод уже проверенным контекстом (`user_id`, и т.п.).
- `Draft` — FSM-черновики для пошагового заполнения. В них включён `ConfigDict(extra="forbid")`, чтобы в state не попадали неожиданные ключи.
- Для дат/времени в `Out` и update-полях используется `AwareDatetime`, то есть timezone-aware `datetime`.
- Поля `created_at` и `updated_at` приходят из моделей через `TimestampMixin`; в `Out` они обязательные `AwareDatetime`.
- Денежные поля описаны через `Decimal` и валидируются как неотрицательные (`ge=0`).
- ID в схемах — внутренние DB id, если явно не написано `telegram_id` / `admin_tg_id`.

---

## User (`schemas/user.py`)

Модель: `db.models.user.User`. Репозиторий: `UserRepository` принимает `UserCreate`, `UserUpdate | UserAdminUpdate`.

### `UserCreate`

Схема для создания клиента.

| Поле | Тип / ограничения | Комментарий |
|---|---|---|
| `telegram_id` | `int` | Уникальный Telegram ID клиента. |
| `username` | `Optional[str]`, `max_length=100` | Telegram username. |
| `first_name` | `Optional[str]`, `max_length=100` | Имя. |
| `last_name` | `Optional[str]`, `max_length=100` | Фамилия. |
| `full_name` | `Optional[str]`, `max_length=200` | Полное имя. |
| `phone` | `Optional[str]`, `max_length=20` | Телефон. |
| `email` | `Optional[str]`, `max_length=100` | Email. |
| `language_code` | `Optional[str]`, `max_length=10` | Язык Telegram-клиента. |

Не передаются в `Create`: `account_status`, `banned_at`, `banned_by_admin_id`, `ban_reason`, `created_at`, `updated_at` — это статусы/аудит/служебные поля модели.

### `UserUpdate`

Схема для обновления профиля клиента. Все поля опциональны:

- `username: Optional[str] = Field(None, max_length=100)`
- `first_name: Optional[str] = Field(None, max_length=100)`
- `last_name: Optional[str] = Field(None, max_length=100)`
- `full_name: Optional[str] = Field(None, max_length=200)`
- `phone: Optional[str] = Field(None, max_length=20)`
- `email: Optional[str] = Field(None, max_length=100)`
- `language_code: Optional[str] = Field(None, max_length=10)`

### `UserOut`

Схема возврата клиента наружу:

- `id: int`
- `telegram_id: int`
- `username: Optional[str] = None`
- `first_name: Optional[str] = None`
- `last_name: Optional[str] = None`
- `full_name: Optional[str] = None`
- `phone: Optional[str] = None`
- `email: Optional[str] = None`
- `language_code: Optional[str] = None`
- `account_status: AccountStatus`
- `banned_at: Optional[AwareDatetime] = None`
- `banned_by_admin_id: Optional[int] = None`
- `ban_reason: Optional[str] = None`
- `created_at: AwareDatetime`
- `updated_at: AwareDatetime`

`model_config = ConfigDict(from_attributes=True)`.

### `UserAdminUpdate`

Админская схема для изменения статуса клиента:

- `account_status: Optional[AccountStatus] = None`
- `banned_at: Optional[AwareDatetime] = None`
- `banned_by_admin_id: Optional[int] = None`
- `ban_reason: Optional[str] = None`

Важно: при бане/разбане бизнес-правила должны жить в сервисе: кто банит, когда выставлять `banned_at`, когда очищать поля бана.

---

## Admin (`schemas/admin.py`)

Модель: `db.models.admins.Admin`. Репозиторий: `AdminRepository` принимает `AdminCreate`, `AdminUpdate`. Отдельно есть audit-модель `AdminAction` и схемы для журнала действий.

### `AdminCreate`

Схема создания менеджера/сотрудника компании:

- `telegram_id: int`
- `username: Optional[str] = Field(None, max_length=100)`
- `full_name: Optional[str] = Field(None, max_length=200)`
- `phone: Optional[str] = Field(None, max_length=20)`
- `role: AdminRole = AdminRole.MANAGER`
- `is_active: bool = True`
- `account_status: AccountStatus = AccountStatus.ACTIVE`

### `AdminUpdate`

Схема обновления сотрудника:

- `username: Optional[str] = Field(None, max_length=100)`
- `full_name: Optional[str] = Field(None, max_length=200)`
- `phone: Optional[str] = Field(None, max_length=20)`
- `role: Optional[AdminRole] = None`
- `is_active: Optional[bool] = None`
- `account_status: Optional[AccountStatus] = None`

### `AdminOut`

Схема возврата сотрудника:

- `id: int`
- `telegram_id: int`
- `username: Optional[str] = None`
- `full_name: Optional[str] = None`
- `phone: Optional[str] = None`
- `role: AdminRole`
- `is_active: bool`
- `account_status: AccountStatus`
- `created_at: AwareDatetime`
- `updated_at: AwareDatetime`

`model_config = ConfigDict(from_attributes=True)`.

### `AdminActionCreate`

Схема записи audit-действия админа:

- `admin_id: Optional[int] = None` — внутренний DB id админа, может быть `None`, если админ удалён/не найден.
- `admin_tg_id: int` — Telegram id админа на момент события.
- `action_type: str = Field(..., min_length=1, max_length=64)`
- `entity_type: str = Field(..., min_length=1, max_length=32)`
- `entity_id: str = Field(..., min_length=1, max_length=64)`
- `note: Optional[str] = Field(None, max_length=255)`
- `payload: Optional[dict[str, object]] = None`

### `AdminActionOut`

То же, что `AdminActionCreate`, плюс:

- `id: int`
- `created_at: AwareDatetime`
- `updated_at: AwareDatetime`

`model_config = ConfigDict(from_attributes=True)`.

---

## Category (`schemas/category.py`)

Модель: `db.models.category.Category`. Репозиторий работает с категориями и подкатегориями, сортирует по `sort_order`, затем `name`, затем `id`; умеет искать уникальность `name`/`slug` внутри одного родителя.

### `CategoryCreate`

Схема создания категории/подкатегории:

- `name: str = Field(..., min_length=1, max_length=128)`
- `emoji: Optional[str] = Field(None, max_length=32)`
- `parent_id: Optional[int] = None`
- `sort_order: int = Field(0, ge=0)`
- `is_active: bool = True`
- `slug: Optional[str] = Field(None, max_length=128)`

### `CategoryUpdate`

Схема обновления категории/подкатегории:

- `name: Optional[str] = Field(None, min_length=1, max_length=128)`
- `emoji: Optional[str] = Field(None, max_length=32)`
- `parent_id: Optional[int] = None`
- `sort_order: Optional[int] = Field(None, ge=0)`
- `is_active: Optional[bool] = None`
- `slug: Optional[str] = Field(None, max_length=128)`

### `CategoryOut`

Схема возврата категории наружу:

- `id: int`
- `name: str`
- `emoji: Optional[str] = None`
- `parent_id: Optional[int] = None`
- `sort_order: int`
- `is_active: bool`
- `slug: Optional[str] = None`
- `created_at: AwareDatetime`
- `updated_at: AwareDatetime`

`model_config = ConfigDict(from_attributes=True)`.

---

## Item и ItemCharacteristic (`schemas/item.py`)

Модели: `db.models.item.Item`, `db.models.item_characteristics.ItemCharacteristic`. Репозиторий: `ItemRepository` принимает `ItemCreate`, `ItemUpdate`; при создании добавляет служебные поля вроде `created_by_admin_id` из контекста.

### `ItemCreate`

Схема создания товара каталога:

- `category_id: int`
- `subcategory_id: Optional[int] = None`
- `title: str = Field(..., min_length=3, max_length=200)`
- `description: Optional[str] = None`
- `short_description: Optional[str] = Field(None, max_length=300)`
- `price: Decimal = Field(..., ge=0)`
- `price_text: Optional[str] = Field(None, max_length=100)`
- `available_quantity: int = Field(1, ge=0)`
- `is_featured: bool = False`
- `sort_order: int = Field(0, ge=0)`
- `min_rental_period: int = Field(1, ge=1)`
- `max_rental_period: Optional[int] = Field(None, ge=1)`

Важно по новой модели: товары каталога создаёт компания/админ, а не клиент. В схеме больше нет старых полей пользовательского объявления: `owner_id`, `location`, `coordinates`, `deposit`, `is_available`, `moderation_reason` и т.п.

### `ItemUpdate`

Схема обновления товара каталога:

- `category_id: Optional[int] = None`
- `subcategory_id: Optional[int] = None`
- `title: Optional[str] = Field(None, min_length=3, max_length=200)`
- `description: Optional[str] = None`
- `short_description: Optional[str] = Field(None, max_length=300)`
- `price: Optional[Decimal] = Field(None, ge=0)`
- `price_text: Optional[str] = Field(None, max_length=100)`
- `available_quantity: Optional[int] = Field(None, ge=0)`
- `is_featured: Optional[bool] = None`
- `sort_order: Optional[int] = Field(None, ge=0)`
- `min_rental_period: Optional[int] = Field(None, ge=1)`
- `max_rental_period: Optional[int] = Field(None, ge=1)`

### `ItemOut`

Схема возврата товара каталога:

- `id: int`
- `category_id: int`
- `subcategory_id: Optional[int] = None`
- `title: str`
- `description: Optional[str] = None`
- `short_description: Optional[str] = None`
- `price: Decimal = Field(..., ge=0)`
- `price_text: Optional[str] = None`
- `available_quantity: int`
- `is_featured: bool`
- `sort_order: int`
- `min_rental_period: int`
- `max_rental_period: Optional[int] = None`
- `status: ItemStatus`
- `views_count: int`
- `orders_count: int`
- `created_at: AwareDatetime`
- `updated_at: AwareDatetime`

`model_config = ConfigDict(from_attributes=True)`.

### `ItemCharacteristicCreate`

Схема создания характеристики товара:

- `item_id: int`
- `name: str = Field(..., min_length=1, max_length=100)`
- `value: str = Field(..., min_length=1, max_length=200)`
- `sort_order: int = Field(0, ge=0)`

### `ItemCharacteristicUpdate`

Схема обновления характеристики товара:

- `name: Optional[str] = Field(None, min_length=1, max_length=100)`
- `value: Optional[str] = Field(None, min_length=1, max_length=200)`
- `sort_order: Optional[int] = Field(None, ge=0)`

### `ItemCharacteristicOut`

Схема возврата характеристики товара:

- `id: int`
- `item_id: int`
- `name: str`
- `value: str`
- `sort_order: int`
- `created_at: AwareDatetime`
- `updated_at: AwareDatetime`

`model_config = ConfigDict(from_attributes=True)`.

### `ItemModerationUpdate`

Админская схема публикации/скрытия/изменения статуса товара:

- `is_featured: Optional[bool] = None`
- `status: Optional[ItemStatus] = None`

Бизнес-правила переходов статуса проверяются сервисом через `status.item_status.can_transition(...)`.

### `ItemAdminOut(ItemOut)`

Админский вывод товара: наследует все поля `ItemOut` и добавляет:

- `created_by_admin_id: Optional[int] = None`
- `updated_by_admin_id: Optional[int] = None`
- `moderated_at: Optional[AwareDatetime] = None`

### `ItemCreateDraft`

FSM-черновик создания товара. Включает `model_config = ConfigDict(extra="forbid")`.

Поля:

- `category_id: Optional[int] = None`
- `subcategory_id: Optional[int] = None`
- `title: Optional[str] = Field(default=None, min_length=3, max_length=200)`
- `description: Optional[str] = None`
- `short_description: Optional[str] = Field(None, max_length=300)`
- `price: Optional[Decimal] = Field(default=None, ge=0)`
- `price_text: Optional[str] = Field(None, max_length=100)`
- `available_quantity: int = Field(1, ge=0)`
- `min_rental_period: int = Field(default=1, ge=1)`
- `max_rental_period: Optional[int] = Field(None, ge=1)`
- `is_featured: bool = False`
- `sort_order: int = Field(0, ge=0)`

---

## Photo (`schemas/photo.py`)

Модель: `db.models.photo.Photo`. Репозиторий сейчас работает аргументами методов (`create(item_id=..., telegram_file_id=..., ...)`, `update(...)`) и поддерживает reorder/main/swap/set_order.

### `PhotoCreate`

Схема создания фотографии товара:

- `item_id: int`
- `telegram_file_id: Optional[str] = Field(None, max_length=500)`
- `url: Optional[str] = Field(None, max_length=1000)`
- `sort_order: int = Field(0, ge=0)`
- `is_main: bool = False`

### `PhotoUpdate`

Схема обновления фотографии:

- `telegram_file_id: Optional[str] = Field(None, max_length=500)`
- `url: Optional[str] = Field(None, max_length=1000)`
- `sort_order: Optional[int] = Field(None, ge=0)`
- `is_main: Optional[bool] = None`

### `PhotoOut`

Схема возврата фото наружу:

- `id: int`
- `item_id: int`
- `telegram_file_id: Optional[str] = None`
- `url: Optional[str] = None`
- `sort_order: int`
- `is_main: bool`
- `created_at: AwareDatetime`
- `updated_at: AwareDatetime`

`model_config = ConfigDict(from_attributes=True)`.

---

## Rental (`schemas/rental.py`)

Модель: `db.models.rental.Rental`. Репозиторий: `RentalRepository` принимает `RentalCreate`, `RentalUpdate`. В новой логике rental — это заявка клиента на аренду товара каталога, а не сделка между владельцем и арендатором.

### `RentalCreate`

Клиентская схема создания заявки на аренду товара:

- `item_id: int`
- `user_id: int`
- `total_price: Optional[Decimal] = Field(None, ge=0)`
- `start_date: Optional[AwareDatetime] = None`
- `end_date: Optional[AwareDatetime] = None`
- `rental_period_text: Optional[str] = Field(None, max_length=100)`
- `quantity: int = Field(1, ge=1)`
- `delivery_needed: Optional[bool] = None`
- `delivery_address: Optional[str] = None`
- `client_name: Optional[str] = Field(None, max_length=150)`
- `client_phone: Optional[str] = Field(None, max_length=30)`
- `client_comment: Optional[str] = None`

Не передаются клиентом: `status`, `final_price`, `manager_comment`, `assigned_admin_id`, служебные timestamps статусов. Их выставляет модель/сервис/менеджер.

### `RentalUpdate`

Схема обновления заявки менеджером или системой:

- `start_date: Optional[AwareDatetime] = None`
- `end_date: Optional[AwareDatetime] = None`
- `rental_period_text: Optional[str] = Field(None, max_length=100)`
- `total_price: Optional[Decimal] = Field(None, ge=0)`
- `final_price: Optional[Decimal] = Field(None, ge=0)`
- `status: Optional[RentalStatus] = None`
- `quantity: Optional[int] = Field(None, ge=1)`
- `delivery_needed: Optional[bool] = None`
- `delivery_address: Optional[str] = None`
- `client_name: Optional[str] = Field(None, max_length=150)`
- `client_phone: Optional[str] = Field(None, max_length=30)`
- `client_comment: Optional[str] = None`
- `manager_comment: Optional[str] = None`
- `assigned_admin_id: Optional[int] = None`
- `in_progress_at: Optional[AwareDatetime] = None`
- `processed_at: Optional[AwareDatetime] = None`
- `closed_at: Optional[AwareDatetime] = None`
- `confirmed_at: Optional[AwareDatetime] = None`
- `rejected_at: Optional[AwareDatetime] = None`
- `cancelled_at: Optional[AwareDatetime] = None`
- `completed_at: Optional[AwareDatetime] = None`

### `RentalOut`

Схема возврата заявки наружу:

- `id: int`
- `item_id: int`
- `user_id: int`
- `start_date: Optional[AwareDatetime] = None`
- `end_date: Optional[AwareDatetime] = None`
- `rental_period_text: Optional[str] = None`
- `total_price: Optional[Decimal] = None`
- `final_price: Optional[Decimal] = None`
- `status: RentalStatus`
- `quantity: int`
- `delivery_needed: Optional[bool] = None`
- `delivery_address: Optional[str] = None`
- `client_name: Optional[str] = None`
- `client_phone: Optional[str] = None`
- `client_comment: Optional[str] = None`
- `manager_comment: Optional[str] = None`
- `assigned_admin_id: Optional[int] = None`
- `in_progress_at: Optional[AwareDatetime] = None`
- `processed_at: Optional[AwareDatetime] = None`
- `closed_at: Optional[AwareDatetime] = None`
- `confirmed_at: Optional[AwareDatetime] = None`
- `rejected_at: Optional[AwareDatetime] = None`
- `cancelled_at: Optional[AwareDatetime] = None`
- `completed_at: Optional[AwareDatetime] = None`
- `created_at: AwareDatetime`
- `updated_at: AwareDatetime`

`model_config = ConfigDict(from_attributes=True)`.

### `RentalDetailsOut`

Полная информация о заявке для клиентского/общего сценария:

- `rental: RentalOut`
- `item: ItemOut`
- `user: UserOut`

`model_config = ConfigDict(from_attributes=True)`.

### `RentalAdminDetailsOut`

Полная информация о заявке для администратора/менеджера:

- `rental: RentalOut`
- `item: ItemOut`
- `user: UserOut`

`model_config = ConfigDict(from_attributes=True)`.

### `RentalCreateDraft`

FSM-черновик пошагового создания заявки. Включает `model_config = ConfigDict(extra="forbid")`.

- `item_id: Optional[int] = None`
- `start_date: Optional[str] = None`
- `end_date: Optional[str] = None`
- `rental_period_text: Optional[str] = Field(None, max_length=100)`
- `quantity: Optional[int] = Field(None, ge=1)`
- `delivery_needed: Optional[bool] = None`
- `delivery_address: Optional[str] = None`
- `client_name: Optional[str] = Field(None, max_length=150)`
- `client_phone: Optional[str] = Field(None, max_length=30)`
- `client_comment: Optional[str] = None`

Важно: в draft даты пока строки (`Optional[str]`), потому что в FSM они приходят/хранятся в пользовательском формате до финальной сборки `RentalCreate`.

---

## Review (`schemas/review.py`)

Модель: `db.models.review.Review`. Репозиторий: `ReviewRepository` принимает `ReviewCreateInternal`, `ReviewUpdate`, `ReviewAdminUpdate`.

### `ReviewCreate`

Клиентская схема создания отзыва по завершённой заявке:

- `rental_id: int`
- `item_id: Optional[int] = None`
- `rating: int = Field(..., ge=1, le=5)`
- `comment: Optional[str] = None`

### `ReviewUpdate`

Схема обновления текста и оценки отзыва клиентом до публикации:

- `rating: Optional[int] = Field(None, ge=1, le=5)`
- `comment: Optional[str] = None`

### `ReviewOut`

Схема возврата отзыва наружу:

- `id: int`
- `rental_id: int`
- `item_id: Optional[int] = None`
- `user_id: int`
- `rating: int`
- `comment: Optional[str] = None`
- `status: ReviewStatus`
- `admin_note: Optional[str] = None`
- `created_at: AwareDatetime`
- `updated_at: AwareDatetime`

`model_config = ConfigDict(from_attributes=True)`.

### `ReviewCreateInternal(ReviewCreate)`

Внутренняя схема создания отзыва с уже определённым клиентом. Наследует все поля `ReviewCreate` и добавляет:

- `user_id: int`

### `ReviewAdminUpdate`

Схема модерации отзыва администратором:

- `status: Optional[ReviewStatus] = None`
- `admin_note: Optional[str] = None`

---

## SupportTicket (`schemas/support.py`)

Модель: `db.models.support_ticket.SupportTicket`. Репозиторий: `SupportTicketRepository` принимает `SupportTicketCreateInternal`, `SupportTicketAdminUpdate`.

### `SupportTicketCreate`

Клиентская схема создания обращения в поддержку:

- `text: str = Field(..., min_length=1)`
- `subject: Optional[str] = Field(None, max_length=150)`
- `item_id: Optional[int] = None`
- `rental_id: Optional[int] = None`

### `SupportTicketOut`

Возврат обращения наружу для клиента/админа:

- `id: int`
- `user_id: int`
- `subject: Optional[str] = None`
- `item_id: Optional[int] = None`
- `rental_id: Optional[int] = None`
- `text: str`
- `status: SupportTicketStatus`
- `closed_at: Optional[AwareDatetime] = None`
- `closed_by_admin_id: Optional[int] = None`
- `admin_last_reply_at: Optional[AwareDatetime] = None`
- `created_at: AwareDatetime`
- `updated_at: AwareDatetime`

`model_config = ConfigDict(from_attributes=True)`.

### `SupportTicketCreateInternal(SupportTicketCreate)`

Внутренняя схема создания обращения с уже определённым клиентом. Наследует все поля `SupportTicketCreate` и добавляет:

- `user_id: int`

### `SupportTicketAdminUpdate`

Схема админского обновления обращения:

- `status: Optional[SupportTicketStatus] = None`
- `closed_at: Optional[AwareDatetime] = None`
- `closed_by_admin_id: Optional[int] = None`
- `admin_last_reply_at: Optional[AwareDatetime] = None`

Важно: при закрытии тикета сервис должен соблюдать консистентность: `closed_at` и `closed_by_admin_id` должны быть заполнены вместе. Это также соответствует check constraint в модели.

---

## Статусы, которые используются в схемах

### `AccountStatus`

Используется в `UserOut`, `UserAdminUpdate`, `AdminCreate`, `AdminUpdate`, `AdminOut`.

- `ACTIVE`
- `BANNED`

### `AdminRole`

Используется в схемах администратора.

- `OWNER`
- `ADMIN`
- `MANAGER`

### `ItemStatus`

Используется в `ItemOut`, `ItemModerationUpdate`.

- `DRAFT`
- `ACTIVE`
- `HIDDEN`
- `ARCHIVED`

### `RentalStatus`

Используется в `RentalUpdate`, `RentalOut`.

- `REQUESTED`
- `IN_PROGRESS`
- `CONFIRMED`
- `REJECTED`
- `COMPLETED`
- `CANCELLED_BY_CLIENT`
- `CANCELLED_BY_ADMIN`

### `ReviewStatus`

Используется в `ReviewOut`, `ReviewAdminUpdate`.

- `PENDING`
- `PUBLISHED`
- `HIDDEN`
- `REJECTED`

### `SupportTicketStatus`

Используется в `SupportTicketOut`, `SupportTicketAdminUpdate`.

- `OPEN`
- `CLOSED`

---

## Как схемы сейчас используются репозиториями

| Репозиторий | Схемы на вход |
|---|---|
| `AdminRepository` | `AdminCreate`, `AdminUpdate` |
| `UserRepository` | `UserCreate`, `UserUpdate`, `UserAdminUpdate` |
| `ItemRepository` | `ItemCreate`, `ItemUpdate` |
| `RentalRepository` | `RentalCreate`, `RentalUpdate` |
| `ReviewRepository` | `ReviewCreateInternal`, `ReviewUpdate`, `ReviewAdminUpdate` |
| `SupportTicketRepository` | `SupportTicketCreateInternal`, `SupportTicketAdminUpdate` |
| `CategoryRepository` | Сейчас работает аргументами методов, но схемы `CategoryCreate/Update/Out` отражают модель. |
| `PhotoRepository` | Сейчас работает аргументами методов, но схемы `PhotoCreate/Update/Out` отражают модель. |

---

## Короткий чек-лист актуальности

- `Item` описывает товар каталога компании, а не пользовательское объявление.
- `Rental` описывает заявку клиента на аренду товара, а не P2P-сделку владелец/арендатор.
- `Review` привязан к `rental_id`, опционально к `item_id`, и обязательно к `user_id` во внутренней схеме.
- `SupportTicket` может быть связан с `item_id` и/или `rental_id`.
- `AdminAction` хранит и `admin_id`, и `admin_tg_id` для audit-истории.
- Все `Out`-схемы для ORM имеют `ConfigDict(from_attributes=True)`.
- Все update-схемы рассчитаны на `exclude_unset=True` в репозиториях.
- Все FSM draft-схемы запрещают лишние поля через `extra="forbid"`.