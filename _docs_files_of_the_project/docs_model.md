# Base

### 1. `admin_tg_id -> admin_id`
Поменял, но возможны будущие ошибки из-за того, что где-то не поменял.

### 2. 
- ✅ `server_default=func.now()`
- ✅ `onupdate=func.now()`

---

# Category

### 1. `id`
- `primary_key=True`
- `autoincrement=True`

### 2.
- `parent_id: ForeignKey("categories.id", ondelete="CASCADE")`
- `sort_order: default=0`
- `is_active: default=True`

## Отношения

`parent`
- `"Category"`
- `remote_side="Category.id"`
- `back_populates="subcategories"` “мои дочерние категории” (связь “вниз”)

`subcategories`
- `"Category"`
- `back_populates="parent"` “мой родитель” (связь “вверх”)
- `cascade="all, delete-orphan"`
- `single_parent=True`
- `passive_deletes=True`

### `__table_args__`
В рамках одного родителя имя уникально:
- `UniqueConstraint("parent_id", "name", name="uq_categories_parent_id_name")`

Защита от «сам себе родитель»:
- `CheckConstraint("parent_id IS NULL OR parent_id <> id", name="ck_categories_no_self_parent")`

Для быстрого получения категорий по `parent_id`:
- `Index("ix_categories_parent_id", "parent_id")`

---

# Item

> Убрал: user id, location, coordinates, deposit, is_available, moderated_by_admin_id, moderation_reason

- `price: Numeric(12, 2)`
- `available_quantity: default=1`
- `is_featured: default=False`
- `moderated_at: DateTime(timezone=True)`
- `sort_order: default=0`
- `min_rental_period: default=1`
- `views_count: default=0`
- `orders_count: default=0`

`is_featured: Boolean` 

- `category_id: ForeignKey("categories.id", ondelete="RESTRICT")` - нельзя удалить категорию, пока есть вещи
- `subcategory_id: ForeignKey("categories.id", ondelete="SET NULL")` - подкатегория может обнулиться
- `created_by_admin_id: ForeignKey("admins.id", ondelete="SET NULL")`
- `updated_by_admin_id: ForeignKey("admins.id", ondelete="SET NULL")`

>`status` 
>- `SAEnum(ItemStatus, name="item_status")`
>- `default=ItemStatus.PENDING`

## Отношения

> Убрал: owner, rentals?

>Ниже отношения, для чего нужны, пример:
> - Без relationship ты можешь получить [только](): `item.category_id`
> - Но с relationship ты можешь сделать: `item.category.name`

`category / subcategory`
- `"Category"`
- `foreign_keys=[category_id / subcategory_id]`

`created_by_admin / updated_by_admin`
- `"Admin"`
- `foreign_keys=[created_by_admin_id / updated_by_admin_id]`

`item_photos`
- `"Photo"` 
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

`characteristics`
- `"ItemCharacteristic"`
- `back_populates="item"`
- `cascade="all, delete-orphan"`
- `single_parent=True`

### `__table_args__`

>Создай индекс, который помогает БД быстро искать товары по **[subcategory_id]()**, потом по **[status]()**, 
>и сразу отдавать их в порядке **[sort_order]()**:
> 
>`Index("ix_items_subcategory_status_sort", "subcategory_id", "status", "sort_order")`

---

# ItemCharacteristic

### 1. 
- `item_id: ForeignKey("items.id", ondelete="CASCADE"))`
- `sort_order: default=0`

### 2.
`item`
- `"Item"`
- `back_populates="characteristics"`

---

# User

[**_Rental здесь — это ...**]()

`telegram_id`
- `BigInteger`
- `unique=True`

- `rating: default=Decimal("0.00")`
- `rating_count: default=0`

- `phone: String(20)`
- `email: String(100)`
- `language_code: String(10)`

`account_status`
- `SAEnum(AccountStatus, name="account_status")`
- `default=AccountStatus.ACTIVE`

- `banned_by_admin_id: ForeignKey("users.id", ondelete="SET NULL")`
- `banned_at: DateTime(timezone=True)`
- `ban_reason: Text`

> Убрал: `rating / rating_count`
>
>рейтинг
>* `rating: Mapped[Decimal] = mapped_column(Numeric(3, 2), nullable=False, default=Decimal("0.00"))`
>* `rating_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)`
> 
> Также убираем
>* `CheckConstraint("rating >= 0 AND rating <= 5", name="ck_users_rating_range"),`
>* `CheckConstraint("rating_count >= 0", name="ck_users_rating_count_non_neg"),`

## Отношения

> Убираем: `items` - в RentalMarketBot пользователи не создают товары. Товары создаёт компания через админов.
```python
    items: Mapped[list["Item"]] = relationship(
        "Item",
        back_populates="owner", # User.items  <->  Item.owner
        foreign_keys="Item.user_id", # связь User.items строится через колонку Item.user_id
        cascade="all, delete-orphan", # Item — дочерняя сущность пользователя: Удалили юзера → удалились его вещи (если в Item FK ondelete=CASCADE — идеально)
        single_parent=True, # вещь принадлежит одному владельцу, а не нескольким
        passive_deletes=True, # если пользователь удаляется, БД сама удалит Item через ondelete="CASCADE"
    )
```

> Убираем: `rentals_as_owner / rentals_as_renter` - это список аренд, где пользователь выступает владельцем/арендатором.
> В новом проекте нет owner-пользователя. Есть клиент и компания.
```python
    rentals_as_owner / rentals_as_renter: Mapped[list["Rental"]] = relationship(
        "Rental", 
        foreign_keys="Rental.owner_id / .renter_id", # потому что Rental связан с User двумя FK: `owner_id` и `renter_id`. Без этого SQLAlchemy не поймёт, какая именно связь нужна.
        back_populates="owner / renter"
    )

# `Cascade`? Нет. И это правильно.  Почему:
#   - аренды — это история
#   - удаление пользователя не должно удалять истории аренды
#   - в `Rental.owner_id` стоит `ondelete="RESTRICT"`
```


Вместо этого новые связи:
- один пользователь может оставить много заявок на аренду
```python
    rental_requests: Mapped[list["RentalRequest"]] = relationship(
        "RentalRequest",
        back_populates="user",
    )
```

- связь с корзиной: один пользователь может добавить несколько товаров в корзину
```python
    cart_items: Mapped[list["CartItem"]] = relationship(
        "CartItem",
        back_populates="user",
        cascade="all, delete-orphan",
        single_parent=True,
    )
```

---

# Rental

**[Заявка клиента на аренду товара.]()**

`item_id: ForeignKey("items.id", ondelete="RESTRICT")`

`start_date / end_date: DateTime(timezone=True)`
  - Если пользователь может выбрать не точные даты, а период: `nullable=True`
  - Сейчас стоит `nullable=False`

`total_price`
  - `nullable=True`: В заявке цена может быть предварительной. Менеджер потом уточняет итоговую стоимость, доставку, срок, наличие.
  - Сейчас стоит `nullable=False`

`status`
- `SAEnum(RentalStatus, name="rental_status")`
- `default=RentalStatus.REQUESTED`

- `quantity: default=1`
- `user_id: ForeignKey("users.id", ondelete="RESTRICT")`
- `assigned_admin_id: ForeignKey("admins.id", ondelete="SET NULL")`
- `processed_at: DateTime(timezone=True)`
- `closed_at: DateTime(timezone=True)`

## Отношения

`item`  - У каждой аренды есть одна вещь
- `"Item"`
- `back_populates="rentals"`

`user`
- `"User"`
- `back_populates="rentals"`

`assigned_admin`
- `"Admin"`
- `foreign_keys=[assigned_admin_id]`

`reviews` - У одной аренды может быть несколько отзывов
- `back_populates="rental"`
- `cascade="all, delete-orphan"`
- `#single_parent=True`
- `#lazy="selectin"`
- `#passive_deletes=True`

```python
# Убрал:

# Арендатор
renter_id: Mapped[int] = mapped_column(
    ForeignKey("users.id", ondelete="RESTRICT"), 
    nullable=False
)

# Владелец
owner_id: Mapped[int] = mapped_column(
    ForeignKey("users.id", ondelete="RESTRICT"), 
    nullable=False
)

deposit_amount: Mapped[Optional[Decimal]] = mapped_column(
    Numeric(12, 2), 
    nullable=True
)

owner_handover_confirmed: Mapped[bool] = mapped_column(
    Boolean, 
    default=False, 
    nullable=False
)

renter_receive_confirmed: Mapped[bool] = mapped_column(
    Boolean, 
    default=False, 
    nullable=False
)

# Удалил эти отношения:
renter: Mapped["User"] = relationship("User", foreign_keys=[renter_id], back_populates="rentals_as_renter")
owner: Mapped["User"] = relationship("User", foreign_keys=[owner_id],  back_populates="rentals_as_owner")

Index("ix_rentals_renter_id", "renter_id"),
Index("ix_rentals_owner_id", "owner_id"),

# история арендатора (история бронирований): renter_id + status
Index("ix_rentals_renter_status", "renter_id", "status"),

# история арендодателя (его подтверждения): owner_id + status
Index("ix_rentals_owner_status", "owner_id", "status"),
```

---

# Admin / AdminAction

[`Admin`— Админ/менеджер компании]()

>`telegram_id`
>- `BigInteger`
>- `unique=True`

>`role`
>- `SAEnum(AdminRole, name="admin_role")`
>- `default=AdminRole.MANAGER`

>`is_active: default=True`

>`account_status`
>- `SAEnum(AccountStatus, name="account_status")`
>- `default=AccountStatus.ACTIVE`


[`AdminAction` — журнал действий администратора]()

`admin_id`
- `ForeignKey("admins.id", ondelete="SET NULL")`

- `admin_tg_id: BigInteger`
- `payload: JSON`

---

# Photo

>`item_id: ForeignKey("items.id", ondelete="CASCADE")`

>- `telegram_file_id: String(500)` - идентификатор файла, который Telegram позволяет использовать повторно
>- `url: String(1000)` - ссылка на фото товара с сайта

>`default`
>- `sort_order: 0` Если явно не задано — фото попадает в базовый порядок
>- `is_main: False` 

---

# SupportTicket

>`status`
>- `SAEnum(SupportTicketStatus, name="support_ticket_status")`
>- `default=SupportTicketStatus.OPEN`

>`DateTime(timezone=True)`
>- `closed_at` / `admin_last_reply_at`

> `ForeignKey`
>- `user_id: ("users.id", ondelete="RESTRICT")`
>- `rental_id: ("rental_requests.id", ondelete="SET NULL")`
>- `closed_by_admin_id: ("admins.id", ondelete="SET NULL")`

> Убрал: `telegram_id` / `username`


---

# Review

>- `rental_id: ForeignKey("rentals.id", ondelete="CASCADE")`
>- `item_id: ForeignKey("items.id", ondelete="SET NULL")`
>- `user_id: ForeignKey("users.id", ondelete="RESTRICT")`

>`status`
>   - `SAEnum(ReviewStatus, name="review_status")`
>   - `default=ReviewStatus.PENDING`

---

# Общее

## Схема проекта

```
  User
   ├─ items -> Item
   ├─ rentals_as_owner -> Rental
   ├─ rentals_as_renter -> Rental
   └─ support_tickets -> SupportTicket
  
  Category
   └─ subcategories -> Category   (self-referential tree)
  
  Item
   ├─ owner -> User
   ├─ category_id -> Category
   ├─ subcategory_id -> Category
   ├─ rentals -> Rental
   └─ item_photos -> Photo
  
  Photo
   └─ item -> Item
  
  Rental
   ├─ item -> Item
   ├─ owner -> User
   ├─ renter -> User
   └─ reviews -> Review
  
  Review
   ├─ rental -> Rental
   ├─ reviewer -> User
   └─ reviewee -> User
  
  SupportTicket
   └─ user -> User
  
  AdminAction
   └─ отдельно, без FK на User
```

## Короткая интуиция по проекту

```
  User
   ├─ владеет Item
   ├─ участвует в Rental
   ├─ пишет/получает Review
   └─ создаёт SupportTicket
  
  Item
   ├─ принадлежит User
   ├─ лежит в Category
   ├─ имеет Photo
   └─ участвует в Rental
  
  Rental
   ├─ связывает Item + owner + renter
   └─ порождает Review
  
  Category
   └─ строит дерево сама с собой
```

---

## Смысла проекта

Это система аренды, где всё крутится вокруг вещей, сделок и их жизненного цикла.

[Пользователь]() — центральная точка: он создаёт вещи, участвует в аренде, получает отзывы и взаимодействует с поддержкой.
Но при этом пользователь — не просто сущность, а носитель истории, поэтому его нельзя удалять, если он участвовал в сделках или оставил след в системе.

[Вещь (Item)]() — это базовый объект предложения.
Она принадлежит пользователю и не существует без него, но сама по себе не является историей — это актив, который может участвовать в сделках.

[Фотографии]() — полностью подчинённые сущности:
они живут только внутри вещи и не имеют смысла без неё.

[Категории]() образуют дерево:
каждая категория может иметь родителя и подкатегории, формируя иерархию, в которой элементы существуют в контексте структуры, а не сами по себе.

[Аренда (Rental)]() — это ключевая доменная сущность.
Она связывает вещь, владельца и арендатора и фиксирует факт взаимодействия.
Это уже не “часть вещи”, а историческая запись, которую нельзя удалять без потери смысла системы.

[Отзывы]() живут внутри контекста аренды:
если нет аренды — отзыв теряет смысл.
Но при этом они связаны с пользователями и становятся частью их репутации, которую тоже нельзя просто удалить.

[Поддержка (SupportTicket)]() — это ещё один слой истории:
запросы пользователя фиксируются как события, которые должны сохраняться независимо от изменений в других частях системы.

Некоторые связи в системе мягкие:
например, подкатегория или администратор, который модерировал вещь.
Если такие сущности исчезают, система не ломается — связь просто обнуляется.

[Аудит]() действий администратора стоит отдельно:
это лог, который фиксирует события как факты, а не как часть связанной ORM-структуры.
Он хранит значения, а не зависит от существования других сущностей.

Это система, где:
- Item — это актив
- Rental — это история
- Review — это репутация
- User — это носитель всех этих связей
- Photo — это чистый дочерний ресурс
- Category — это структура
- SupportTicket — это след взаимодействия
- AdminAction — это лог событий

---

Category
### 1. `nullable`
- `True`: `emoji` / `parent_id` / `slug`
- `False`: `name` / `sort_order` / `is_active`

Item
### 1. `nullable`
- `True`: `subcategory_id` / `description` / `short_description` / `price_text` / `created_by_admin_id` 
/ `updated_by_admin_id` / `moderated_at` / `max_rental_period` / 
- `False`: `category_id` / `title` / `price` / `available_quantity` / `is_featured` / `sort_order` 
/ `status` / `min_rental_period` / `views_count` / `orders_count`

ItemCharacteristic
### 1. `nullable`
- `True`:
- `False`: `item_id` / `name` / `value` / `sort_order`

User
### 1. `nullable`
- `True`: `username` / `telegram_id` / `phone` / `email` / `language_code` /
`banned_at` / `banned_by_admin_id` / `ban_reason`
- `False`: `item_id` / `account_status`

Rental
### 1. `nullable`
- `True`: `rental_period_text` / `` / `` / ``
- `False`: `item_id` / `start_date` / `end_date` / `total_price` / `status` / `quantity`

---

# Параметры

`nullable`
`default`