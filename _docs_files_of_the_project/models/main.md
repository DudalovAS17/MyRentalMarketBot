# Документация по моделям БД

Документ описывает актуальные SQLAlchemy-модели проекта RentalMarketBot: поля, связи, ограничения, индексы и доменную роль каждой таблицы.


---

# Короткая доменная интуиция

`Admin` — сотрудник компании, который ведёт каталог, заявки, поддержку и оставляет след в аудите.

`AdminAction` — исторический лог действий админов. Он должен сохранять факт действия даже если часть связей потом обнулится.

`Category` — структура каталога. Категории образуют дерево через `parent_id`.

`Item` — актив компании, который можно показывать в каталоге и сдавать в аренду.

`ItemCharacteristic` — дочернее описание товара. Без `Item` характеристика не имеет смысла.

`Photo` — дочерний ресурс товара. Без `Item` фотография не имеет смысла.

`User` — клиент, который создаёт заявки, пишет в поддержку и оставляет отзывы. Он не владеет товарами каталога.

`Rental` — историческая заявка на аренду. Это центр операционного процесса: клиент выбрал товар, указал контакты/сроки/доставку, менеджер обработал заявку.

`Review` — репутационная запись после заявки. Она привязана к `Rental`, автору `User` и опционально к `Item`.

`SupportTicket` — след коммуникации клиента с компанией. Может быть связан с товаром или заявкой, но не обязан.

---

# id (везде)
- `Integer`
- `primary_key=True`
- `autoincrement=True`

---

# Base

## `Base`

`Base` — общий декларативный класс для всех моделей.

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

> Время ставит БД, а не приложение. Это полезно, чтобы `created_at / updated_at` были консистентными независимо от сервера, где запущен бот.

---

# Admin

`Admin` — сотрудник компании: владелец, админ или менеджер.

## Поля

`id`: `primary_key=True` / `autoincrement=True`

`telegram_id` - Telegram ID администратора: `BigInteger` / `unique=True`

`phone`: `String(20)`

`role` - роли: `OWNER`, `ADMIN`, `MANAGER`: 
- `SAEnum(AdminRole, name="admin_role")`
- `default=AdminRole.MANAGER`

`is_active` - быстрый флаг доступа к админке: `Boolean` / `default=True`


`account_status` - статусы: `ACTIVE`, `BANNED`:
- `SAEnum(AccountStatus, name="account_status")`
- `default=AccountStatus.ACTIVE`


## Отношения

`created_items` - список товаров, созданных админом:
- связь с `Item.created_by_admin_id`
- `back_populates="created_by_admin"`

`updated_items` - список товаров, обновлённых админом:
- связь с `Item.updated_by_admin_id`
- `back_populates="updated_by_admin"`

`closed_support_tickets` - тикеты, закрытые админом:
- связь с `SupportTicket.closed_by_admin_id`
- `back_populates="closed_by_admin"`

`admin_actions` - журнал действий администратора:
- `back_populates="admin"`

`assigned_rentals` - заявки на аренду, назначенные на менеджера:
- связь с `Rental.assigned_admin_id`
- `back_populates="assigned_admin"`

## Индексы
- `Index("ix_admins_account_status", "account_status")`
- `Index("ix_admins_username", "username")`
- `Index("ix_admins_role", "role")`
- `Index("ix_admins_is_active", "is_active")`

---

# AdminAction

`AdminAction` — аудит действий администраторов.

> Это лог событий. Он хранит факт действия и payload, а не пытается быть полноценной связанной доменной сущностью.

## Поля

`admin_id` - если админ удалён, запись аудита остаётся:
- `ForeignKey("admins.id", ondelete="SET NULL")`

`admin_tg_id` - Telegram ID сохраняется отдельно, чтобы в аудите остался идентификатор даже при обнулении `admin_id`.

`action_type` - что сделал админ: создать товар, подтвердить заявку, закрыть тикет и т.д.

`entity_type` - тип сущности: `rental`, `item`, `user`, `admin`, `support_ticket`.

`entity_id` - универсальный ID сущности. Хранится строкой, чтобы лог мог работать с разными типами идентификаторов.

`note` - короткая человеко-читаемая заметка.

`payload`: `JSON` - детали действия: причина, резолюция, старый статус, metadata и т.д.

## Отношения

`admin` - связь с `Admin`:
- `back_populates="admin_actions"`

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

`Category` — дерево категорий и подкатегорий каталога товаров компании.

## Поля

`parent_id`
- `ForeignKey("categories.id", ondelete="CASCADE")`
- `NULL` означает корневую категорию.

`sort_order` - порядок отображения:
- `default=0`

`is_active` - показывать или скрывать категорию:
- `Boolean`
- `default=True`

`slug` - машинное имя для callback/deeplink/seed-данных.

## Отношения

`parent` - родительская категория:
- `remote_side="Category.id"`
- `back_populates="subcategories"` - “мои дочерние категории” (связь “вниз”)

`subcategories` - дочерние категории:
- `back_populates="parent"` - “мой родитель” (связь “вверх”)
- `cascade="all, delete-orphan"`
- `single_parent=True`
- `passive_deletes=True`

> Если удалить родительскую категорию, дочерние категории удаляются каскадно на уровне БД/ORM.

## `__table_args__`

Уникальность внутри одного родителя:
- `UniqueConstraint("parent_id", "name", name="uq_categories_parent_id_name")`
- `UniqueConstraint("parent_id", "slug", name="uq_categories_parent_id_slug")`

Защита от «сам себе родитель»:
- `CheckConstraint("parent_id IS NULL OR parent_id <> id", name="ck_categories_no_self_parent")`

Порядок не может быть отрицательным:
- `CheckConstraint("sort_order >= 0", name="ck_categories_sort_order_non_neg")`

Индексы (для быстрого получения категорий по ..):
- `Index("ix_categories_parent_id", "parent_id")`
- `Index("ix_categories_parent_active", "parent_id", "is_active")`
- `Index("ix_categories_sort_order", "sort_order")`

---

# Item

`Item` — товар каталога компании для аренды.

> Товары создаёт и ведёт компания через админов.

## Поля

`category_id` - нельзя удалить категорию, пока в ней есть товары:
- `ForeignKey("categories.id", ondelete="RESTRICT")`

`subcategory_id` - если подкатегория удалена, товар остаётся, а связь обнуляется:
- `ForeignKey("categories.id", ondelete="SET NULL")`

`price` - цена аренды, сейчас используется как базовая цена/цена за день:
- `Numeric(12, 2)`

`price_text` - человеко-читаемый текст цены, если нужна гибкая подпись.

`available_quantity` - количество в наличии:
- `default=1`

`is_featured` - рекомендованный товар:
- `Boolean`
- `default=False`

`sort_order` - порядок отображения внутри категории/подкатегории:
- `default=0`

`status` - статусы: `DRAFT`, `ACTIVE`, `HIDDEN`, `ARCHIVED`:
- `SAEnum(ItemStatus, name="item_status")`
- `default=ItemStatus.DRAFT`

`created_by_admin_id`
- `ForeignKey("admins.id", ondelete="SET NULL")`

`updated_by_admin_id`
- `ForeignKey("admins.id", ondelete="SET NULL")`

`moderated_at`
- `DateTime(timezone=True)`

`min_rental_period` - минимальный срок аренды в днях:
- `default=1`
 
`max_rental_period` - максимальный срок аренды, если ограничен.

`views_count`: `default=0`

`orders_count`: `default=0`

## Отношения

`category` - связь с `Category` через `category_id`

`subcategory` - связь с `Category` через `subcategory_id`

`rentals` - заявки на аренду этого товара:
- `back_populates="item"`.

`item_photos` - фотографии товара:
- `back_populates="item"` Photo — настоящая дочерняя сущность Item
- `cascade="all, delete-orphan"` удалил вещь → удалили её фото (фото не имеет смысла без вещи)
- `single_parent=True` одно фото принадлежит одной вещи

>Убрал `passive_deletes=True`, почему:
>- Представь: У тебя есть Item с 100 Photo. 
>- Ты делаешь: `session.delete(item)`.
>- Что делает ORM (по умолчанию):
>    * ORM идёт в БД и загружает все 100 фото
>    * Потом удаляет их по одному
>    * Потом удаляет Item.
>
> То есть: `SELECT photos... - DELETE photo 1 - DELETE photo 2 - ... - DELETE photo 100 - DELETE item`
> 👉 Это много лишней работы.
>
> Что происходит с `passive_deletes=True`:
>- Ты говоришь ORM: “Не трогай детей. Пусть БД сама всё сделает.”
>И при этом у тебя в БД уже есть:
>`FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE`.
>Тогда происходит: `DELETE item`. И ВСЁ.
>- А БД сама удаляет все связанные photo

> Фото — настоящая дочерняя сущность `Item`. Без товара фото не имеет смысла.

`characteristics` - характеристики товара:
- `back_populates="item"`
- `cascade="all, delete-orphan"`
- `single_parent=True`

`created_by_admin` - админ, который создал товар:
- `back_populates="created_items"`

`updated_by_admin` - админ, который последним обновил товар:
- `back_populates="updated_items"`

`reviews` - отзывы по товару:
- `back_populates="item"`

`support_tickets` - обращения поддержки по товару:
- `back_populates="item"`

---

# ItemCharacteristic

`ItemCharacteristic` — техническая/визуальная характеристика товара: вес, мощность, габариты, глубина уплотнения и т.д.

## Поля

`item_id`: `ForeignKey("items.id", ondelete="CASCADE")`

`sort_order`: `default=0`

## Отношения

`item` - связь с `Item`:
- `back_populates="characteristics"`

---

# Photo

`Photo` — фотография товара каталога.

## Поля

`item_id`: `ForeignKey("items.id", ondelete="CASCADE")`

`telegram_file_id` - Telegram `file_id`, чтобы повторно отправлять фото без новой загрузки

`url` - ссылка на фото с сайта или внешнего источника

`sort_order` - порядок показа фото внутри карточки:
- `default=0`

`is_main` - главное фото товара:
- `Boolean`
- `default=False`

## Отношения

`item` - связь с `Item`:
- `back_populates="item_photos"`

> Важно: в модели есть TODO — ограничение «одно главное фото на товар» пока нужно контролировать на уровне сервиса или добавить DB-specific partial unique index.

---

# User

`User` — клиент бота.

## Поля

`account_status` - статусы: `ACTIVE`, `BANNED`:
- `SAEnum(AccountStatus, name="account_status")`
- `default=AccountStatus.ACTIVE`

`banned_at`: `DateTime(timezone=True)`

`banned_by_admin_id`: `ForeignKey("admins.id", ondelete="SET NULL")`

## Отношения

`rentals` - заявки клиента на аренду:
- `back_populates="user"`

`support_tickets` - обращения клиента в поддержку:
- `back_populates="user"`

`banned_by_admin` - админ, который заблокировал пользователя:
- связь через `banned_by_admin_id`

`reviews` - отзывы пользователя:
- `back_populates="user"`

> Каталог принадлежит компании, а клиент создаёт заявки на аренду.

---

# Rental

`Rental` — заявка клиента на аренду товара.

> Это ключевая историческая сущность: она связывает клиента, товар, менеджера, цены, сроки, доставку и финальный статус обработки.

## Поля


`item_id` - товар нельзя удалить, пока на него есть заявки:
- `ForeignKey("items.id", ondelete="RESTRICT")`

`start_date`: `DateTime(timezone=True)`

`end_date`: `DateTime(timezone=True)`

`rental_period_text` - текстовое описание срока аренды, если клиент выбрал период не только датами.

`total_price` - предварительная/расчётная цена:
- `Numeric(12, 2)`

`final_price` - итоговая согласованная цена:
- `Numeric(12, 2)`

`status` - статусы: `REQUESTED`, `IN_PROGRESS`, `CONFIRMED`, `REJECTED`, `CANCELLED_BY_CLIENT`, `CANCELLED_BY_ADMIN`, `COMPLETED`:
- `SAEnum(RentalStatus, name="rental_status")`
- `default=RentalStatus.REQUESTED`

`quantity`: `default=1`

`delivery_needed`: `Boolean`

`user_id`: `ForeignKey("users.id", ondelete="RESTRICT")`

`manager_comment` - внутренний комментарий менеджера.

`assigned_admin_id` - назначенный менеджер
- `ForeignKey("admins.id", ondelete="SET NULL")`

`DateTime(timezone=True)`:
- `in_progress_at`
- `processed_at`
- `closed_at`
- `confirmed_at`
- `rejected_at`
- `cancelled_at`
- `completed_at`

> Эти timestamp-поля нужны для аналитики: время обработки, доля отмен, среднее время до завершения и т.д.

## Отношения

`item` - арендуемый товар:
- `back_populates="rentals"`

`user` - клиент, который оставил заявку:
- `back_populates="rentals"`

`assigned_admin` - менеджер, назначенный на заявку:
- `back_populates="assigned_rentals"`

`reviews` - отзывы по заявке:
- `back_populates="rental"`
- `cascade="all, delete-orphan"`

`support_tickets` - обращения поддержки по заявке:
- `back_populates="rental"`

---

# Review

`Review` — отзыв клиента о товаре/аренде/сервисе в контексте конкретной заявки.

## Поля

`rental_id` - отзыв не имеет смысла без заявки:
- `ForeignKey("rentals.id", ondelete="CASCADE")`
 
`item_id` - товар можно обнулить, но сам отзыв как часть истории заявки остаётся:
- `ForeignKey("items.id", ondelete="SET NULL")`

`user_id` - пользователя нельзя удалить, если от него есть отзыв:
- `ForeignKey("users.id", ondelete="RESTRICT")`

`rating` - оценка от 1 до 5:

`status` - статусы: `PENDING`, `PUBLISHED`, `HIDDEN`, `REJECTED`:
- `SAEnum(ReviewStatus, name="review_status")`
- `default=ReviewStatus.PENDING`

`admin_note` - внутренняя заметка админа по модерации.

## Отношения

`rental` - заявка, к которой относится отзыв:
- `back_populates="reviews"`

`user` - автор отзыва:
- `back_populates="reviews"`

`item` - товар, о котором оставлен отзыв:
- `back_populates="reviews"`

---

# SupportTicket

`SupportTicket` — обращение клиента в поддержку.

## Поля

`user_id` - обращение всегда принадлежит пользователю:
- `ForeignKey("users.id", ondelete="RESTRICT")`

`text` - основной текст обращения.

`subject` - короткая тема для админки.

`item_id` - если обращение связано с товаром:
- `ForeignKey("items.id", ondelete="SET NULL")`

`rental_id` - если обращение связано с заявкой:
- `ForeignKey("rentals.id", ondelete="SET NULL")`

`status` - статусы: `OPEN`, `CLOSED`:
- `SAEnum(SupportTicketStatus, name="support_ticket_status")`
- `default=SupportTicketStatus.OPEN`

`closed_at`: `DateTime(timezone=True)`

`closed_by_admin_id`: `ForeignKey("admins.id", ondelete="SET NULL")`

`admin_last_reply_at` - когда админ в последний раз отвечал по тикету:
- `DateTime(timezone=True)`

## Отношения

`user` - клиент, создавший обращение:
- `back_populates="support_tickets"`

`item` - товар, к которому относится обращение:
- `back_populates="support_tickets"`

`rental` - заявка, к которой относится обращение:
- `back_populates="support_tickets"`

`closed_by_admin` - админ, закрывший тикет:
- `back_populates="closed_support_tickets"`