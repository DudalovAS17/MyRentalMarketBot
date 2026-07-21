# Base

## `Base`

`Base` — общий декларативный класс для всех SQLAlchemy-моделей.

### `metadata`

Используется единый `naming_convention`, чтобы Alembic и БД создавали предсказуемые имена для:
- `ix` — индексов;
- `uq` — уникальных ограничений;
- `ck` — check-constraint;
- `fk` — foreign key;
- `pk` — primary key.

## `TimestampMixin`

Добавляет во все основные модели:

`created_at`
- `DateTime(timezone=True)`
- `server_default=func.now()`
- `nullable=False`

`updated_at`
- `DateTime(timezone=True)`
- `server_default=func.now()`
- `onupdate=func.now()`
- `nullable=False`

> Время ставит БД, а не приложение. Это помогает держать `created_at / updated_at` консистентными независимо от хоста, где запущен бот.

`enum_values()`
- `enum_cls` — это Enum-класс
- `__members__.values()` — его элементы
- `member.value` — значение enum

---

# везде

`id`: `Integer` / `primary_key=True` /`autoincrement=True`

---

# Admin

`Admin` — сотрудник компании.

## Поля
`telegram_id` — Telegram ID администратора:
- `BigInteger`
- `unique=True`

`role` — роль сотрудника: `MANAGER/OWNER/ADMIN`
- `SAEnum(AdminRole, name="admin_role")`
- `default=AdminRole.MANAGER`

`is_active` — быстрый флаг доступа к админке:
- `Boolean`
- `default=True`

`account_status` — статус аккаунта: `ACTIVE/BANNED`
- `SAEnum(AccountStatus, name="account_status")`
- `default=AccountStatus.ACTIVE`


## Отношения
`created_items` — товары, созданные админом:
- связь с `Item.created_by_admin_id`
- `back_populates="created_by_admin"`

`updated_items` — товары, обновлённые админом:
- связь с `Item.updated_by_admin_id`
- `back_populates="updated_by_admin"`

`closed_support_tickets` — тикеты, закрытые админом:
- связь с `SupportTicket.closed_by_admin_id`
- `back_populates="closed_by_admin"`

`admin_actions` — audit-записи администратора:
- `back_populates="admin"`

`assigned_rentals` — заявки, назначенные на менеджера:
- связь с `Rental.assigned_admin_id`
- `back_populates="assigned_admin"`

## Индексы
- `Index("ix_admins_account_status", "account_status")`
- `Index("ix_admins_username", "username")`
- `Index("ix_admins_role", "role")`
- `Index("ix_admins_is_active", "is_active")`

---

# AdminAction

`AdminAction` — журнал действий администратора.

> Это лог событий. Он хранит факт действия и payload, а не пытается быть полноценной доменной сущностью.

## Поля
`admin_id` — ссылка на админа:
- `ForeignKey("admins.id", ondelete="SET NULL")`

`admin_tg_id` — Telegram ID админа, сохранённый отдельно:

`action_type` — что сделал админ

`entity_type` — тип сущности

`entity_id` — универсальный ID сущности:

`note` — короткая человеко-читаемая заметка

`payload` — детали действия: `JSON`

## Отношения
`admin` — связь с `Admin`:
- `back_populates="admin_actions"`
- может быть `NULL`, если админ удалён.

## Индексы
- `Index("ix_admin_actions_admin_id", "admin_id")`
- `Index("ix_admin_actions_admin_tg_id", "admin_tg_id")`
- `Index("ix_admin_actions_action_type", "action_type")`
- `Index("ix_admin_actions_entity_type", "entity_type")`
- `Index("ix_admin_actions_entity_id", "entity_id")`
- `Index("ix_admin_actions_entity", "entity_type", "entity_id")`
- `Index("ix_admin_actions_admin_entity", "admin_id", "entity_type", "entity_id")`

---

# Category

`Category` — категории и подкатегории каталога товаров компании.

## Поля
`parent_id` — родительская категория: `ForeignKey("categories.id", ondelete="RESTRICT")`
- Было `CASCADE`: Удалил родительскую категорию → автоматически удалились все подкатегории
- Сейчас `RESTRICT`: Нельзя удалить категорию, если у неё есть подкатегории

`sort_order` — порядок отображения: `default=0`

`is_active` — показывать/скрывать категорию: `Boolean`

`slug` — машинное имя для callback/deeplink/seed-данных

## Отношения
`parent` — родительская категория:
- `remote_side="Category.id"`
- `back_populates="subcategories"`

`subcategories` — дочерние категории:
- `back_populates="parent"`
- `cascade="all, delete-orphan"`
- `single_parent=True`
- `passive_deletes=True`

## Ограничения и индексы
- `UniqueConstraint("parent_id", "name", name="uq_categories_parent_id_name")`
- `UniqueConstraint("parent_id", "slug", name="uq_categories_parent_id_slug")`
- `CheckConstraint("parent_id IS NULL OR parent_id <> id", name="ck_categories_no_self_parent")`
- `CheckConstraint("sort_order >= 0", name="ck_categories_sort_order_non_neg")`
- `Index("ix_categories_parent_id", "parent_id")`
- `Index("ix_categories_parent_active", "parent_id", "is_active")`
- `Index("ix_categories_sort_order", "sort_order")`

> В модели есть TODO: при необходимости добавить DB-specific partial unique indexes для корневых категорий по `name/slug`.

---

# Item
`Item` — товар каталога компании для аренды.

## Поля
`category_id` — основная категория: `ForeignKey("categories.id", ondelete="RESTRICT")`

`subcategory_id` — подкатегория: `ForeignKey("categories.id", ondelete="SET NULL")`

`price` — цена за период/день по доменной логике сервиса: `Numeric(12, 2)`

`available_quantity` — количество в наличии: `default=1`

`is_featured` — рекомендуемый товар:
- `Boolean`
- `default=False`

`sort_order` — порядок отображения: `default=0`

`status` — статус карточки: `DRAFT/ACTIVE/HIDDEN/ARCHIVED`
- `SAEnum(ItemStatus, name="item_status")`
- `default=ItemStatus.DRAFT`

`created_by_admin_id` — кто создал товар: `ForeignKey("admins.id", ondelete="SET NULL")`

`updated_by_admin_id` — кто последним обновил товар: `ForeignKey("admins.id", ondelete="SET NULL")`

`moderated_at` — когда товар модерировали/обновили с точки зрения публикации: `DateTime(timezone=True)`

`min_rental_period` — минимальный срок аренды в днях: `default=1`

`max_rental_period` — максимальный срок аренды в днях:

`views_count` — количество просмотров: `default=0`

`orders_count` — количество заявок: `default=0`

## Отношения
`category` — основная категория:
- связь с `Category` по `category_id`

`subcategory` — подкатегория:
- связь с `Category` по `subcategory_id`
- может быть `NULL`

`rentals` — заявки по товару:
- `back_populates="item"`

`item_photos` — фотографии товара:
- `back_populates="item"`
- `cascade="all, delete-orphan"`
- `single_parent=True`

`characteristics` — характеристики товара:
- `back_populates="item"`
- `cascade="all, delete-orphan"`
- `single_parent=True`

`created_by_admin` — админ-создатель: `back_populates="created_items"`

`updated_by_admin` — админ, который обновил товар: `back_populates="updated_items"`

`reviews` — отзывы по товару: `back_populates="item"`

`support_tickets` — обращения поддержки по товару: `back_populates="item"`

## Ограничения и индексы
- `CheckConstraint("price >= 0", name="ck_items_price_non_neg")`
- `CheckConstraint("min_rental_period >= 1", name="ck_items_min_period")`
- `CheckConstraint("(max_rental_period IS NULL) OR (max_rental_period >= min_rental_period)", name="ck_items_max_ge_min")`
- `CheckConstraint("sort_order >= 0", name="ck_items_sort_order_non_neg")`
- `CheckConstraint("available_quantity >= 0", name="ck_items_available_quantity_non_neg")`
- `CheckConstraint("views_count >= 0", name="ck_items_views_non_neg")`
- `CheckConstraint("orders_count >= 0", name="ck_items_orders_non_neg")`
- `Index("ix_items_category_id", "category_id")`
- `Index("ix_items_subcategory_id", "subcategory_id")`
- `Index("ix_items_status", "status")`
- `Index("ix_items_category_status", "category_id", "status")`
- `Index("ix_items_subcategory_status", "subcategory_id", "status")`
- `Index("ix_items_featured", "is_featured")`
- `Index("ix_items_sort_order", "sort_order")`
- `Index("ix_items_subcategory_status_sort", "subcategory_id", "status", "sort_order")`

---

# ItemCharacteristic

`ItemCharacteristic` — техническая характеристика товара.

## Поля
`item_id` — товар: `ForeignKey("items.id", ondelete="CASCADE")`

`sort_order` — порядок отображения: `default=0`

## Отношения
`item` — товар:
- `back_populates="characteristics"`

## Ограничения и индексы
- `CheckConstraint("sort_order >= 0", name="ck_item_characteristics_sort_order_non_neg")`
- `UniqueConstraint("item_id", "name", name="uq_item_characteristics_item_id_name")`
- `Index("ix_item_characteristics_item_id", "item_id")`
- `Index("ix_item_characteristics_item_sort_order", "item_id", "sort_order")`

---

# Photo

`Photo` — фотография товара каталога.

## Поля
`item_id` — товар: `ForeignKey("items.id", ondelete="CASCADE")`

`url` — ссылка на изображение из внешнего источника

`sort_order` — порядок отображения внутри карточки: `default=0`

`is_main` — главное фото товара:
- `Boolean`
- `default=False`

## Отношения
`item` — товар: `back_populates="item_photos"`

## Ограничения и индексы
- `Index("ix_photos_item_order", "item_id", "sort_order")`
- `Index("ix_photos_item_main", "item_id", "is_main")`
- `CheckConstraint("sort_order >= 0", name="ck_photos_order_non_neg")`
- `CheckConstraint("(telegram_file_id IS NOT NULL) OR (url IS NOT NULL)", name="ck_photos_has_source")`

> В модели есть TODO: ограничить одно главное фото на товар на уровне БД или сервиса.

---

# User

`User` — клиент Telegram-бота.

## Поля
`telegram_id` — Telegram ID клиента:
- `BigInteger`
- `unique=True`

`account_status` — статус аккаунта: `ACTIVE/BANNED`
- `SAEnum(AccountStatus, name="account_status")`
- `default=AccountStatus.ACTIVE`

`banned_at` — когда заблокировали: `DateTime(timezone=True)`

`banned_by_admin_id` — кто заблокировал: `ForeignKey("admins.id", ondelete="SET NULL")`

## Отношения
`rentals` — заявки пользователя: `back_populates="user"`

`support_tickets` — обращения пользователя: `back_populates="user"`

`banned_by_admin` — админ, заблокировавший пользователя:
- связь с `Admin` по `banned_by_admin_id`

`reviews` — отзывы пользователя: `back_populates="user"`

## Индексы
- `Index("ix_users_account_status", "account_status")`
- `Index("ix_users_username", "username")`
- `Index("ix_users_telegram_id", "telegram_id")`
- `Index("ix_users_phone", "phone")`

---

# Rental

`Rental` — заявка клиента на аренду товара.

## Поля

`item_id` — арендуемый товар:  `ForeignKey("items.id", ondelete="RESTRICT")`

`total_price` — предварительная сумма: `Numeric(12, 2)`

`final_price` — финальная согласованная сумма: `Numeric(12, 2)`

`status` — статус заявки: `REQUESTED/IN_PROGRESS/CONFIRMED/REJECTED/COMPLETED/CANCELLED_BY_CLIENT/CANCELLED_BY_ADMIN`
- `SAEnum(RentalStatus, name="rental_status")`
- `default=RentalStatus.REQUESTED`

`quantity` — количество единиц товара: `default=1`

`user_id` — клиент: `ForeignKey("users.id", ondelete="RESTRICT")`

`assigned_admin_id` — назначенный менеджер: `ForeignKey("admins.id", ondelete="SET NULL")`

`in_progress_at` — когда заявку взяли в работу: `DateTime(timezone=True)`

`processed_at` — время обработки/служебная отметка: `DateTime(timezone=True)`

`closed_at` — когда заявка закрыта: `DateTime(timezone=True)`

`confirmed_at` — когда подтверждена: `DateTime(timezone=True)`

`rejected_at` — когда отклонена: `DateTime(timezone=True)`

`cancelled_at` — когда отменена: `DateTime(timezone=True)`

`completed_at` — когда завершена: `DateTime(timezone=True)`


## Отношения
`item` — арендуемый товар: `back_populates="rentals"`

`user` — клиент: `back_populates="rentals"`

`assigned_admin` — назначенный менеджер: `back_populates="assigned_rentals"`

`reviews` — отзывы по заявке:
- `back_populates="rental"`
- `cascade="all, delete-orphan"`

`support_tickets` — обращения поддержки по заявке: `back_populates="rental"`

## Ограничения и индексы
- `CheckConstraint("(total_price IS NULL) OR (total_price >= 0)", name="ck_rentals_total_price_non_neg")`
- `CheckConstraint("(final_price IS NULL) OR (final_price >= 0)", name="ck_rentals_final_price_non_neg")`
- `CheckConstraint("quantity >= 1", name="ck_rentals_quantity_positive")`
- `Index("ix_rentals_item_id", "item_id")`
- `Index("ix_rentals_status", "status")`
- `Index("ix_rentals_user_id", "user_id")`
- `Index("ix_rentals_user_status", "user_id", "status")`
- `Index("ix_rentals_assigned_admin_status", "assigned_admin_id", "status")`
- `Index("ix_rentals_item_status", "item_id", "status")`

---

# Review

`Review` — отзыв клиента о товаре, заявке или сервисе компании.

## Поля
`rental_id` — заявка, в рамках которой оставлен отзыв: `ForeignKey("rentals.id", ondelete="CASCADE")`

`item_id` — товар, если отзыв относится к товару: `ForeignKey("items.id", ondelete="SET NULL")`

`user_id` — автор отзыва: `ForeignKey("users.id", ondelete="RESTRICT")`

`rating` — оценка от 1 до 5

`comment` — текст отзыва

`status` — статус модерации: `PENDING/PUBLISHED/HIDDEN/REJECTED`
- `SAEnum(ReviewStatus, name="review_status")`
- `default=ReviewStatus.PENDING`

`admin_note` — внутренняя заметка админа

## Отношения
`rental` — заявка: `back_populates="reviews"`

`user` — автор: `back_populates="reviews"`

`item` — товар:
- `back_populates="reviews"`
- может быть `NULL`

## Ограничения и индексы
- `Index("ix_reviews_rental_id", "rental_id")`
- `Index("ix_reviews_user_id", "user_id")`
- `Index("ix_reviews_item_id", "item_id")`
- `Index("ix_reviews_status", "status")`
- `Index("ix_reviews_item_rating", "item_id", "rating")`
- `Index("ix_reviews_rental_user", "rental_id", "user_id")`
- `Index("ix_reviews_item_status", "item_id", "status")`
- `CheckConstraint("rating >= 1 AND rating <= 5", name="ck_reviews_rating_range")`
- `UniqueConstraint("rental_id", "user_id", name="uq_reviews_rental_user")`

---

# SupportTicket

`SupportTicket` — обращение клиента в поддержку.

## Поля

`user_id` — автор обращения: `ForeignKey("users.id", ondelete="RESTRICT")`

`text` — основное содержание обращения

`subject` — короткая тема для админки

`item_id` — товар, если обращение связано с товаром: `ForeignKey("items.id", ondelete="SET NULL")`

`rental_id` — заявка, если обращение связано с заявкой: `ForeignKey("rentals.id", ondelete="SET NULL")`

`status` — статус обращения: `OPEN/CLOSED`
- `SAEnum(SupportTicketStatus, name="support_ticket_status")`
- `default=SupportTicketStatus.OPEN`

`closed_at` — когда закрыли тикет: `DateTime(timezone=True)`

`closed_by_admin_id` — кто закрыл тикет: `ForeignKey("admins.id", ondelete="SET NULL")`

`admin_last_reply_at` — когда админ последний раз отвечал: `DateTime(timezone=True)`

## Отношения
`user` — клиент: `back_populates="support_tickets"`

`item` — товар:
- `back_populates="support_tickets"`
- может быть `NULL`

`rental` — заявка:
- `back_populates="support_tickets"`
- может быть `NULL`

`closed_by_admin` — админ, который закрыл тикет:
- `back_populates="closed_support_tickets"`
- может быть `NULL`

## Ограничения и индексы
- `CheckConstraint("(closed_at IS NULL AND closed_by_admin_id IS NULL) OR (closed_at IS NOT NULL AND closed_by_admin_id IS NOT NULL)", name="ck_support_tickets_closed_fields_consistent")`
- `Index("ix_support_tickets_user_id", "user_id")`
- `Index("ix_support_tickets_status", "status")`
- `Index("ix_support_tickets_user_status", "user_id", "status")`
- `Index("ix_support_tickets_status_created", "status", "created_at")`
- `Index("ix_support_tickets_item_id", "item_id")`
- `Index("ix_support_tickets_rental_id", "rental_id")`
- `Index("ix_support_tickets_closed_by_admin_id", "closed_by_admin_id")`
- `Index("ix_support_tickets_request_status", "rental_id", "status")`