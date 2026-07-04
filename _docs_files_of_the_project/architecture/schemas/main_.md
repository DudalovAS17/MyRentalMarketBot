# Документация по схемам проекта

Документ описывает актуальные Pydantic-схемы из `schemas/` и их связь с текущей доменной моделью: Telegram-бот компании по аренде товаров.

Сейчас проект не является marketplace-ом пользовательских объявлений. Поэтому в схемах нет актуальных `owner_id`, `renter_id`, `deposit`, `location`, `is_available`, `reviewee_id` и других старых полей пользовательского рынка. Компания ведёт каталог, клиент создаёт заявку, менеджер обрабатывает заявку.

---

## 0. Общие правила схем

### Типы схем

- `Create` — входные данные для создания сущности.
- `Update` — patch-схема для изменения сущности. Обычно все поля `Optional`; репозитории применяют `model_dump(exclude_unset=True)`.
- `Out` — DTO наружу для handlers/services. Для ORM-объектов используется `model_config = ConfigDict(from_attributes=True)`.
- `Admin...` — схемы админского вывода или админского update/moderation.
- `Internal` — внутренняя схема сервиса, которая дополняет клиентский ввод проверенным контекстом (`user_id`, и т.п.).
- `Draft` — FSM-черновик для пошагового заполнения. В таких схемах используется `ConfigDict(extra="forbid")`.

### Общие технические договорённости

- Даты в DTO описываются через `AwareDatetime`.
- Денежные поля описываются через `Decimal` и валидируются `ge=0`.
- В `Out` почти всегда есть `created_at` и `updated_at`, потому что ORM-модели наследуют `TimestampMixin`.
- ID без уточнения — внутренние DB id.
- Telegram ID всегда явно называется `telegram_id` или `admin_tg_id`.
- Схемы не должны содержать бизнес-логику переходов статусов; это задача сервисов и `status/*.py`.

---

## 1. User (`schemas/user.py`)

Модель: `db.models.user.User`.
Репозиторий: `UserRepository`.

Клиент Telegram-бота. Используется для регистрации, профиля, банов и связи с заявками/тикетами/отзывами.

### `UserCreate`

Создание клиента.

| Поле | Тип / ограничения | Комментарий |
|---|---|---|
| `telegram_id` | `int` | Уникальный Telegram ID клиента. |
| `username` | `Optional[str]`, `max_length=100` | Telegram username. |
| `first_name` | `Optional[str]`, `max_length=100` | Имя из Telegram/профиля. |
| `last_name` | `Optional[str]`, `max_length=100` | Фамилия. |
| `full_name` | `Optional[str]`, `max_length=200` | Полное имя. |
| `phone` | `Optional[str]`, `max_length=20` | Телефон; нужен для завершения регистрации. |
| `email` | `Optional[str]`, `max_length=100` | Email. |
| `language_code` | `Optional[str]`, `max_length=10` | Язык Telegram-клиента. |

Не передаём в `UserCreate`: `account_status`, поля бана, timestamps.

### `UserUpdate`

Patch профиля клиента:
- `username`
- `first_name`
- `last_name`
- `full_name`
- `phone`
- `email`
- `language_code`

Все поля optional и имеют те же max-length ограничения, что в `UserCreate`.

### `UserOut`

Возврат клиента наружу:
- `id`, `telegram_id`;
- профильные поля;
- `account_status: AccountStatus`;
- audit-поля бана: `banned_at`, `banned_by_admin_id`, `ban_reason`;
- `created_at`, `updated_at`.

`model_config = ConfigDict(from_attributes=True)`.

### `UserAdminUpdate`

Админский patch статуса клиента:
- `account_status: Optional[AccountStatus]`;
- `banned_at: Optional[AwareDatetime]`;
- `banned_by_admin_id: Optional[int]`;
- `ban_reason: Optional[str]`.

Бизнес-правила бана/разбана живут в `UserService`, а не в схеме.

---

## 2. Admin и AdminAction (`schemas/admin.py`)

Модели:
- `db.models.admins.Admin`;
- `db.models.admin_actions.AdminAction`.

Репозитории:
- `AdminRepository`;
- `AdminActionRepository`.

---

## 2.1. Admin

### `AdminCreate`

Создание менеджера/сотрудника компании:
- `telegram_id: int`;
- `username: Optional[str]`, `max_length=100`;
- `full_name: Optional[str]`, `max_length=200`;
- `phone: Optional[str]`, `max_length=20`;
- `role: AdminRole = AdminRole.MANAGER`;
- `is_active: bool = True`;
- `account_status: AccountStatus = AccountStatus.ACTIVE`.

### `AdminUpdate`

Patch сотрудника:
- `username`;
- `full_name`;
- `phone`;
- `role: Optional[AdminRole]`;
- `is_active: Optional[bool]`;
- `account_status: Optional[AccountStatus]`.

### `AdminOut`

Возврат сотрудника наружу:
- `id`, `telegram_id`;
- `username`, `full_name`, `phone`;
- `role`, `is_active`, `account_status`;
- `created_at`, `updated_at`.

---

## 2.2. AdminAction

Audit-запись действия сотрудника.

### `AdminActionCreate`

- `admin_id: Optional[int] = None` — внутренний ID сотрудника, nullable.
- `admin_tg_id: int` — Telegram ID сотрудника на момент действия.
- `action_type: str`, `min_length=1`, `max_length=64`.
- `entity_type: str`, `min_length=1`, `max_length=32`.
- `entity_id: str`, `min_length=1`, `max_length=64`.
- `note: Optional[str]`, `max_length=255`.
- `payload: Optional[dict[str, object]]`.

Хотя в `status/admin_status.py` есть enum-ы `AdminActionType` и `AdminEntityType`, схема хранит эти поля как строки. Whitelist/выбор enum-а делается уровнем сервиса/handlers.

### `AdminActionOut`

То же, что create, плюс:
- `id`;
- `created_at`;
- `updated_at`.

---

## 3. Category (`schemas/category.py`)

Модель: `db.models.category.Category`.
Репозиторий: `CategoryRepository`.

Категории и подкатегории каталога компании.

### `CategoryCreate`

- `name: str`, `min_length=1`, `max_length=128`;
- `emoji: Optional[str]`, `max_length=32`;
- `parent_id: Optional[int]`;
- `sort_order: int = 0`, `ge=0`;
- `is_active: bool = True`;
- `slug: Optional[str]`, `max_length=128`.

`parent_id=None` — корневая категория. `parent_id=X` — подкатегория.

### `CategoryUpdate`

Patch категории:
- `name`;
- `emoji`;
- `parent_id`;
- `sort_order`;
- `is_active`;
- `slug`.

Важно: схема есть, но в актуальном `CategoryRepository` публичного `update` сейчас нет.

### `CategoryOut`

- `id`, `name`, `emoji`, `parent_id`;
- `sort_order`, `is_active`, `slug`;
- `created_at`, `updated_at`.

---

## 4. Item и ItemCharacteristic (`schemas/item.py`)

Модели:
- `db.models.item.Item`;
- `db.models.item_characteristics.ItemCharacteristic`.

Репозиторий: `ItemRepository`.

Товар — карточка каталога компании для аренды.

---

## 4.1. Item

### `ItemCreate`

Создание товара каталога:
- `category_id: int`;
- `subcategory_id: Optional[int] = None`;
- `title: str`, `min_length=3`, `max_length=200`;
- `description: Optional[str]`;
- `short_description: Optional[str]`, `max_length=300`;
- `price: Decimal`, `ge=0`;
- `price_text: Optional[str]`, `max_length=100`;
- `available_quantity: int = 1`, `ge=0`;
- `is_featured: bool = False`;
- `sort_order: int = 0`, `ge=0`;
- `min_rental_period: int = 1`, `ge=1`;
- `max_rental_period: Optional[int]`, `ge=1`.

Служебные поля `status`, `created_by_admin_id`, `updated_by_admin_id`, `moderated_at`, counters не приходят от клиента/admin-form напрямую через `ItemCreate`: их добавляет сервис/репозиторий.

### `ItemUpdate`

Patch товара. Поля те же, что в `ItemCreate`, но optional.

`status` здесь отсутствует: статус меняется отдельной админской схемой/методом (`ItemModerationUpdate`, `ItemService.admin_set_status`, `ItemRepository.set_status`).

### `ItemOut`

Возврат товара:
- основные поля товара;
- `status: ItemStatus`;
- `views_count`, `orders_count`;
- `created_at`, `updated_at`.

### `ItemAdminOut`

Расширяет `ItemOut` полями:
- `created_by_admin_id`;
- `updated_by_admin_id`;
- `moderated_at`.

### `ItemModerationUpdate`

Админская схема публикации/скрытия:
- `is_featured: Optional[bool]`;
- `status: Optional[ItemStatus]`.

### `ItemCreateDraft`

FSM-черновик создания товара.

Особенности:
- `model_config = ConfigDict(extra="forbid")`;
- поля соответствуют `ItemCreate`, но большинство optional/default;
- используется в `ItemCreateStates`;
- не содержит фото: фотографии в FSM хранятся отдельно списком `photos`.

---

## 4.2. ItemCharacteristic

Характеристики товара: вес, мощность, габариты и т.п.

### `ItemCharacteristicCreate`

- `item_id: int`;
- `name: str`, `min_length=1`, `max_length=100`;
- `value: str`, `min_length=1`, `max_length=200`;
- `sort_order: int = 0`, `ge=0`.

### `ItemCharacteristicUpdate`

Patch:
- `name`;
- `value`;
- `sort_order`.

### `ItemCharacteristicOut`

- `id`, `item_id`, `name`, `value`, `sort_order`;
- `created_at`, `updated_at`.

---

## 5. Photo (`schemas/photo.py`)

Модель: `db.models.photo.Photo`.
Репозиторий: `PhotoRepository`.

Фотография товара каталога.

### `PhotoCreate`

- `item_id: int`;
- `telegram_file_id: Optional[str]`, `max_length=500`;
- `url: Optional[str]`, `max_length=1000`;
- `sort_order: int = 0`, `ge=0`;
- `is_main: bool = False`.

Важно: Pydantic-схема не проверяет «telegram_file_id или url обязателен», но DB-модель содержит check constraint `ck_photos_has_source`.

### `PhotoUpdate`

Patch фото:
- `telegram_file_id`;
- `url`;
- `sort_order`;
- `is_main`.

### `PhotoOut`

- `id`, `item_id`;
- `telegram_file_id`, `url`;
- `sort_order`, `is_main`;
- `created_at`, `updated_at`.

---

## 6. Rental (`schemas/rental.py`)

Модель: `db.models.rental.Rental`.
Репозиторий: `RentalRepository`.

Заявка клиента на аренду товара компании. Это не старая сделка owner/renter.

### `RentalCreate`

Создание заявки:
- `item_id: int`;
- `user_id: int`;
- `total_price: Optional[Decimal]`, `ge=0`;
- `rental_period_text: Optional[str]`, `max_length=100`;
- `delivery_needed: Optional[bool]`;
- `delivery_address: Optional[str]`;
- `client_name: Optional[str]`, `max_length=150`;
- `client_phone: Optional[str]`, `max_length=30`;
- `client_comment: Optional[str]`.

`user_id` должен приходить из проверенного контекста middleware/service, а не из доверенного пользовательского ввода.

### `RentalUpdate`

Patch заявки менеджером/системой:
- период/цены: `rental_period_text`, `total_price`, `final_price`;
- workflow: `status: Optional[RentalStatus]`;
- количество: `quantity`;
- доставка и контактные поля клиента;
- `manager_comment`;
- `assigned_admin_id`;
- timestamp-поля статусов: `in_progress_at`, `processed_at`, `closed_at`, `confirmed_at`, `rejected_at`, `cancelled_at`, `completed_at`.

Статусные переходы проверяются сервисом и `status/rental_status.py`; схема только описывает patch.

### `RentalOut`

Базовый DTO заявки:
- `id`, `item_id`, `user_id`;
- период/цены/status/quantity;
- доставка, клиентские контакты, комментарии;
- `assigned_admin_id`;
- timestamp-поля;
- `created_at`, `updated_at`.

### `RentalDetailsOut`

Композиция:
- `rental: RentalOut`;
- `item: ItemOut`;
- `user: UserOut`.

Для клиентского подробного вывода заявки.

### `RentalAdminDetailsOut`

Сейчас имеет тот же состав, что `RentalDetailsOut`:
- `rental`;
- `item`;
- `user`.

Отдельный класс нужен для будущего расширения админского вывода без ломки клиентского DTO.

### `RentalCreateDraft`

FSM-черновик создания заявки.

Особенности:
- `model_config = ConfigDict(extra="forbid")`;
- `item_id` optional, потому что draft заполняется пошагово;
- хранит `rental_period_text`, delivery-поля, `client_name`, `client_phone`, `client_comment`, `total_price`;
- старые `start_date/end_date` и `quantity` сейчас закомментированы/не используются в активном flow.

---

## 7. Review (`schemas/review.py`)

Модель: `db.models.review.Review`.
Репозиторий: `ReviewRepository`.

Отзыв клиента по завершённой заявке/товару.

### `ReviewCreate`

Клиентская схема:
- `rental_id: int`;
- `item_id: Optional[int] = None`;
- `rating: int`, `ge=1`, `le=5`;
- `comment: Optional[str]`.

`user_id` не принимает от клиента: он добавляется через `ReviewCreateInternal`.

### `ReviewCreateInternal`

Расширяет `ReviewCreate`:
- `user_id: int`.

Используется после проверки текущего пользователя.

### `ReviewUpdate`

Patch до публикации:
- `rating: Optional[int]`, `ge=1`, `le=5`;
- `comment: Optional[str]`.

### `ReviewAdminUpdate`

Админская модерация:
- `status: Optional[ReviewStatus]`;
- `admin_note: Optional[str]`.

### `ReviewOut`

- `id`, `rental_id`, `item_id`, `user_id`;
- `rating`, `comment`;
- `status: ReviewStatus`;
- `admin_note`;
- `created_at`, `updated_at`.

---

## 8. SupportTicket (`schemas/support.py`)

Модель: `db.models.support_ticket.SupportTicket`.
Репозиторий: `SupportTicketRepository`.

Обращение клиента в поддержку.

### `SupportTicketCreate`

Клиентская схема:
- `text: str`, `min_length=1`;
- `subject: Optional[str]`, `max_length=150`;
- `item_id: Optional[int]`;
- `rental_id: Optional[int]`.

### `SupportTicketCreateInternal`

Расширяет `SupportTicketCreate`:
- `user_id: int`.

Используется сервисом после определения текущего клиента.

### `SupportTicketOut`

- `id`, `user_id`;
- `subject`, `item_id`, `rental_id`;
- `text`, `status: SupportTicketStatus`;
- `closed_at`, `closed_by_admin_id`, `admin_last_reply_at`;
- `created_at`, `updated_at`.

### `SupportTicketAdminUpdate`

Админский patch:
- `status: Optional[SupportTicketStatus]`;
- `closed_at: Optional[AwareDatetime]`;
- `closed_by_admin_id: Optional[int]`;
- `admin_last_reply_at: Optional[AwareDatetime]`.

Инвариант закрытия соблюдает сервис/репозиторий: если тикет закрывается, `closed_at` и `closed_by_admin_id` должны быть заполнены вместе.

---

## 9. Практические правила для разработки

1. **Не добавлять старые marketplace-поля в актуальные схемы.** `owner_id/renter_id/deposit/location` сейчас не часть текущей модели.
2. **Для patch-операций использовать `exclude_unset=True`.** Это позволяет отличить «не передали поле» от «передали `None`».
3. **Для ответа из ORM использовать `from_attributes=True`.** Иначе DTO не сможет валидироваться из SQLAlchemy-объекта.
4. **FSM draft хранить отдельно от create-схемы.** Draft может быть неполным, create-схема должна быть финально валидной.
5. **Пользовательские `Create` не должны принимать доверенные служебные поля.** Например, `user_id` в internal-схемах должен приходить из middleware/service context.
6. **Статусы менять через сервисы.** Схемы только описывают допустимый тип поля, но не проверяют workflow.