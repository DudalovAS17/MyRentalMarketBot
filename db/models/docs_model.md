
---

## Base

### 1. `nullable=False`

Запрещает хранить NULL в колонке на уровне БД. У каждой записи ВСЕГДА есть время создания и обновления.

Тогда 

a) Если поле `nullable=False`,
```
if rental.created_at is not None:  # ❌ лишний шум
```

b) `Optional[datetime]` + `nullable=False` — плохо, т.к. 
* `Optional` говорит: “может быть None”, 
* но `nullable=False` говорит: “никогда не None”


### 2. `admin_tg_id -> admin_id`

Поменял, но возможны будущие ошибки из-за того, что где-то не поменял.

### 3. Убрали `class ReprMixin` и `class DictMixin`

### 4.

```
    ✅server_default=func.now(),
    ❌default=lambda: datetime.now(timezone.utc),
```

```
    ✅server_default=func.now(),
    ✅onupdate=func.now(),
    ❌default=lambda: datetime.now(timezone.utc),
    ❌onupdate=lambda: datetime.now(timezone.utc),
```

### 5. Тут все норм, но обдумай.
Единые имена для PK/FK/индексов/уника_лок (удобно для Alembic и чтения схемы)
```
NAMING_CONVENTION: Final[dict[str, str]] = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}
```

---

## Category

### 1. `id`
- `primary_key=True`

Это поле является первичным ключом таблицы. 
Первичный ключ — это главный способ отличать одну запись от другой.

Поле `id`:

    * уникально для каждой записи;
    * не может быть NULL;
    * используется БД как главный идентификатор строки.

- `autoincrement=True`

Значение `id` БД будет увеличивать автоматически при создании новой записи.

### 2. `parent_id`
- `ForeignKey("categories.id", ondelete="CASCADE")` 
    * если удалить родительскую категорию, БД удалит и дочерние категории;
    * делает дерево категорий жёстко зависимым от родителя;
    * подкатегория не считается самостоятельной сущностью без родителя.

- #`index=True` - быстрее выборки по `parent_id`

### Отношения

### 3. `parent` (`categories`)
- `remote_side="Category.id"`
  * self-referential relationship без remote_side для SQLAlchemy неоднозначна;
  * говорит ORM, что именно Category.id является “удалённой” стороной связи;
  * иначе SQLAlchemy не сможет корректно понять, где родитель, а где потомок.

_**self-referential relationship**_ — это связь модели самой с собой. 
В твоём случае `Category` ссылается на `Category`: у категории есть `id`, у категории есть `parent_id`. 
`parent_id` указывает на другую запись в той же таблице `categories`. 
То есть одна и та же таблица хранит: и родительские категории, и подкатегории.

- `back_populates = "subcategories" \ "parent"`
    * `parent` — “мой родитель” (связь “вверх”)
    * `subcategories` — “мои дочерние категории” (связь “вниз”)

`back_populates` говорит SQLAlchemy: эти две связи — две стороны одной и той же relationship. 
Склеивает их в одну согласованную ORM-связь

### 4. `subcategories`

- `back_populates="parent"`

- `cascade="all, delete-orphan"`
    * если дочерняя категория перестала принадлежать родителю, ORM считает её “сиротой” и удаляет
    * это соответствует модели, где подкатегория не должна жить отдельно от дерева
    * `delete-orphan` в self-referential связи опасен без `single_parent=True`

- `single_parent=True`
    * SQLAlchemy требует `single_parent=True`, когда используется `delete-orphan` и объект должен иметь только одного владельца
    * одна подкатегория может иметь только одного родителя

- ` # passive_deletes=True` - уважаем `ondelete` на стороне БД
    * ORM не будет пытаться сама заранее грузить дочерние записи и удалять их по одной
    * она доверяет delete-семантике БД (`ondelete="CASCADE"`)
    * это снижает лишнюю ORM-активность и лучше согласует поведение с FK-правилами БД

### 5. `__table_args__`
В рамках одного родителя имя уникально
- `UniqueConstraint("parent_id", "name", name="uq_categories_parent_id_name")`
    * одинаковые имена допустимы в разных ветках дерева
    * но внутри одного родителя имя должно быть уникально
    * это значит, что уникальность категории в системе — локальная относительно parent_id, а не глобальная

Защита от «сам себе родитель»
- `CheckConstraint("parent_id IS NULL OR parent_id <> id", name="ck_categories_no_self_parent")`
    * это только защита от тривиального цикла “сам себе родитель”
    * она не защищает от более длинных циклов вида A → B → C → A
    * значит модель БД запрещает самый грубый случай, но не решает полную задачу ацикличности дерева

- [CheckConstraint - валидации на уровне БД]() (последняя линия обороны)

Для быстрого получения категорий по parent_id
- `Index("ix_categories_parent_id", "parent_id")`
    * индекс нужен, потому что основной частый запрос — получить всех детей конкретного родителя;
    * без индекса выборка подкатегорий по `parent_id` будет хуже масштабироваться;
    * это индекс под типовой traversal дерева, а не просто “на всякий случай”.

---

## Item

### 1. `user_id` - владелец
`ForeignKey("users.id", ondelete="CASCADE")` - удалил пользователя → снеслись его объявления

### 2. `category_id`
`ForeignKey("categories.id", ondelete="RESTRICT")` - нельзя удалить категорию, пока есть вещи

### 3. `subcategory_id`
`ForeignKey("categories.id", ondelete="SET NULL")` - подкатегория может обнулиться

### 4. `price` / `deposit` - `Numeric(12, 2)`

Decimal/Numeric — без проблем округления.

### 5. `coordinates` - JSON

`[dict[str, Any]],   {"lat": ..., "lng": ...}`

### 6. `status` 
- `SAEnum(ItemStatus, name="item_status")` # String(20)
- `default=ItemStatus.PENDING`

### 7. `moderated_at` - `DateTime(timezone=True)`

### 8. `moderated_by_admin_id` - `ForeignKey("users.id", ondelete="SET NULL")` # Integer

### 9. `min_rental_period` - `default=1`

### 10. `views_count` / `orders_count` - `default=0`

## Отношения

### 11. `owner` 
- `back_populates="items"` 
- `foreign_keys=[user_id]`

### 12. `category` / `subcategory` - нужны?

### 13. `rentals`
- `back_populates="item"` 

Убрал `cascade="all, delete-orphan`, почему:
у `Rental.item_id стоит ForeignKey("items.id", ondelete="RESTRICT")`,
значит: вещь с историей аренды удалять нельзя.
Следовательно, удаление Item не должно автоматически удалять Rental.

А `cascade="all, delete-orphan"` здесь как раз означал бы:
удалил `Item` → ORM начинает удалять связанные `Rental`.
Это противоречит смыслу модели аренды как исторически значимой сущности.

### 12. `item_photos`
- `back_populates="item"` Photo — настоящая дочерняя сущность Item
- `cascade="all, delete-orphan"` удалил вещь → удалили её фото (фото не имеет смысла без вещи)
- `single_parent=True` одно фото принадлежит одной вещи

Убрал `passive_deletes=True`, почему:
- Представь: У тебя есть Item с 100 Photo.
- Ты делаешь: session.delete(item)
- Что делает ORM (по умолчанию):
    * ORM идёт в БД и загружает все 100 фото
    * Потом удаляет их по одному
    * Потом удаляет Item
- То есть:
```
SELECT photos...
DELETE photo 1
DELETE photo 2
...
DELETE photo 100
DELETE item
```
👉 Это много лишней работы.

Что происходит с `passive_deletes=True`
- Ты говоришь ORM: “Не трогай детей. Пусть БД сама всё сделает.”
И при этом у тебя в БД уже есть:
`FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE`
Тогда происходит: `DELETE item`. И ВСЁ.
- А БД сама: → удаляет все связанные photo


---

## Rental

[**_Rental здесь — это узел, который связывает Item + двух User + Review_**]()

### 1. `item_id`
`ForeignKey("items.id", ondelete="RESTRICT")`

### 2. `renter_id` / `owner_id`
`ForeignKey("users.id", ondelete="RESTRICT")`

["RESTRICT" - не даём удалить вещь с историей аренды / арендатора с историями / владельца с историями]()

### 3. `start_date` / `end_date`
`DateTime(timezone=True)`

### 4. `status`
- `SAEnum(RentalStatus, name="rental_status")`
- `default=RentalStatus.REQUESTED`

### 5. `owner_handover_confirmed` / `renter_receive_confirmed`
- `default=False`
- потом заменятся через Alembic?

## Отношения

### 6. `item`  - У каждой аренды есть одна вещь
- `back_populates="rentals"`

### 7. `renter` - У аренды есть один арендатор
- `back_populates="rentals_as_renter"`
- `foreign_keys=[renter_id]`

Здесь `foreign_keys` потому что `Rental` связан с `User` двумя разными FK: `renter_id` \ `owner_id`.
Если не указать `foreign_keys`, SQLAlchemy не поймёт, через какой именно FK строить связь.

### 8. `owner` - У аренды есть один владелец вещи
- `back_populates="rentals_as_owner"`
- `foreign_keys=[owner_id]`

### 9. `reviews` - У одной аренды может быть несколько отзывов
- `back_populates="rental"`
- `cascade="all, delete-orphan"`
- `#single_parent=True`
- `#lazy="selectin"`
- `#passive_deletes=True`

---

## User

[**_Rental здесь — это узел, который связывает Item + двух User + Review_**]()

### 1. `telegram_id`
- `BigInteger`
- `unique=True`

### 2. `rating`
- `default=Decimal("0.00")`

### 3. `rating_count`
- `default=0`

### 4. `account_status`
- `SAEnum(AccountStatus, name="account_status")`
- `default=AccountStatus.ACTIVE`

### 5. `banned_by_admin_id`
- `ForeignKey("users.id", ondelete="SET NULL")` # было Integer

## Отношения

### 6. `items`  - У каждой аренды есть одна вещь
- `back_populates="owner"` - [User.items  <->  Item.owner]()
- `foreign_keys="Item.user_id"` - [связь User.items строится через колонку Item.user_id]()
- `cascade="all, delete-orphan"` (Item — дочерняя сущность пользователя)
  * Удалили юзера → удалились его вещи (если в Item FK ondelete=CASCADE — идеально)
- `single_parent=True` - [вещь принадлежит одному владельцу, а не нескольким]()
- `passive_deletes=True` 
    * ORM доверяет delete-семантике БД
    * если пользователь удаляется, БД сама удалит Item через ondelete="CASCADE"
    * ORM не обязана загружать все Item и удалять их по одной

### 7. `rentals_as_owner` - [Это список аренд, где пользователь выступает владельцем]()
- `foreign_keys="Rental.owner_id"` - потому что Rental связан с User двумя FK: `owner_id` и `renter_id`. 
Без этого SQLAlchemy не поймёт, какая именно связь нужна.
- `back_populates="owner"`

Cascade? Нет. И это правильно.  Почему:
 * аренды — это история
 * удаление пользователя не должно удалять истории аренды
 * в `Rental.owner_id` стоит `ondelete="RESTRICT"`

### 8. `rentals_as_renter` = [Это список аренд, где пользователь выступает арендатором]()
- `foreign_keys="Rental.renter_id"`
- `back_populates="renter"`

### 9. `support_tickets - [У пользователя может быть много тикетов поддержки]()
- `back_populates="user"`

Почему нет cascade

Это логично, потому что:

- тикет поддержки — часть истории взаимодействия;
- `SupportTicket.user_id` стоит с `ondelete="RESTRICT"`;
- удаление пользователя не должно уничтожать историю обращений. 

Смысл: это не дочерний disposable-объект вроде `Photo`, а исторически значимая сущность

---

## Admin

[**_`AdminAction` здесь — это журнал действий администратора_**]()

Это не доменная сущность вроде `Rental` или `Item`, а audit/event record:
- кто сделал действие;
- какое действие;
- над какой сущностью;
- с какими деталями.

[То есть модель отвечает не за “состояние чего-то”, а за фиксирование факта события.]()

### 1. `action_type`, `entity_type`, `entity_id`
- сервис обязан приводить их к str

### 2. `payload`
- `JSON`

---

## Photo

[**_`Photo` — это не самостоятельная сущность уровня `Item` или `Rental`_**]()

Это модель, которая отвечает на вопросы:
- к какой вещи относится фото;
- как получить идентификатор файла;
- в каком порядке это фото показывать.

То есть по смыслу:
[Photo живёт только внутри Item и не имеет самостоятельной ценности вне вещи.]()

### 1. `item_id`
- `ForeignKey("items.id", ondelete="CASCADE")`

### 2. `telegram_file_id`
- здесь мы храним как file_id из Telegram, так и URL?

### 3. `order`
- `default=0` (Если явно не задано — фото попадает в базовый порядок)

---

## SupportTicket

[**_`SupportTicket` — модель уже не ресурса, а истории взаимодействия пользователя с системой_**]()

```
  Поддержка — полный дизайн (MVP)
  
  Главная идея: Поддержка = тикеты, которые создают пользователи.
  
  Админ видит тикеты в админке, может:
  - открыть тикет
  - ответить пользователю
  - закрыть тикет
  
  Пользователь:
  - инициирует обращение (“Написать в поддержку”)
  - получает ответ
  - видит статус “принято/закрыто” (минимально)
```

### 1. `user_id`
- `ForeignKey("users.id", ondelete="RESTRICT")`

### 2. `telegram_id` и `username` убрал

### 3. `status`
- `SAEnum(SupportTicketStatus, name="support_ticket_status")`
- `default=SupportTicketStatus.OPEN`

### 4. `closed_at` и `admin_last_reply_at`
- `DateTime(timezone=True)`

---

## Review

[**_`Review` — это уже не ресурс, а репутационная сущность, привязанная к сделке_**]()

- относится к конкретной аренде;
- влияет на репутацию пользователей.

Review отвечает на вопрос: кто, о ком, по какой сделке и с какой оценкой оставил отзыв.

То есть отзыв у тебя:
- не существует сам по себе;
- не существует без сделки;
- не является просто “комментарием пользователя”;
- это формализованная репутационная запись внутри контекста аренды.

### 1. `rental_id`
- `ForeignKey("rentals.id", ondelete="CASCADE")`

### 2. `reviewer_id` и `reviewee_id`
- `ForeignKey("users.id", ondelete="RESTRICT")`

(Удаление юзера → удалились отзывы. Не подходит. История сделок/репутации должна сохраняться)

## Отношения

### 3. `reviewer` и `reviewee`
- `foreign_keys=[reviewer_id]` (Без foreign_keys ORM не поймёт, по какому полю строить эту связь: reviewer_id или reviewee_id)
- #`lazy="joined"`

---

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

Главный принцип:
- **_родитель_** = сущность, от которой зависит другая;
- **_child_** = живёт “под” родителем;
- **_историческая связь_** = удалять родителя нельзя, пока есть история;
- **_мягкая ссылка_** = связь есть, но при удалении можно обнулить.

Это видно по `relationship(...)`, `cascade=...` и особенно по `ForeignKey(..., ondelete=...)` в моделях

### A. `User -> Item` = родитель → дочерняя сущность

Почему:
- в `Item.user_id` -> `users.id` стоит `ondelete="CASCADE"`
- в `User.items` стоит `cascade="all, delete-orphan"` и `single_parent=True`

**Смысл:**
- вещь принадлежит пользователю;
- без владельца эта вещь в текущей модели не должна жить.

Мысленно:
```
User (родитель)
  └─ Item (дочерняя сущность)
```

### B. `Item -> Photo` = родитель → дочерняя сущность

Почему:
- `Photo.item_id` -> `items.id` с `ondelete="CASCADE"`
- `Item.item_photos` с `cascade="all, delete-orphan"` и `single_parent=True`

**Смысл**: фото не существует отдельно от вещи.

Мысленно:
```
Item (родитель)
  └─ Photo (дочерняя сущность)
```

### C. `Category -> Category` = дерево, self-referential relationship

Почему:
- `Category.parent_id -> categories.id`
- `parent` и `subcategories` связывают категорию саму с собой

**Смысл**: одна категория может быть родителем для подкатегорий.

Мысленно:
```
Category (родитель)
  └─ Category (подкатегория)
```

## История / нельзя удалять (не “родитель-ребёнок”)

### D. `Item -> Rental` - историческая связь.

Почему:
- `Rental.item_id` -> `items.id` с `ondelete="RESTRICT"`
- у `Item.rentals` нет `delete-orphan` каскада

**Смысл**: 
- аренда — это история сделки;
- нельзя удалить `item`, если по ней есть история аренды.

Мысленно:
```
Item
  └─ Rental
```

### E. `User -> Rental` - историческая связь.

Почему:
- `Rental.renter_id` и `Rental.owner_id` обе с `ondelete="RESTRICT"`

**Смысл**: 
- нельзя удалять пользователя, если он участвовал в арендах;
- аренда хранит историю владельца и арендатора.

Мысленно:
```
User (owner)  ─┐
               ├─ Rental (история сделки)
User (renter) ─┘
```

### F. `Rental -> Review` - это ближе к дочерней сущности сделки.

Почему:
- `Review.rental_id` -> `rentals.id` с `ondelete="CASCADE"`
- `Rental.reviews` с `cascade="all, delete-orphan"`

Смысл:
- отзыв живёт внутри контекста конкретной аренды;
- если аренды нет, отзыв теряет смысл.

Мысленно:
```
Rental (родитель)
  └─ Review (дочерняя сущность сделки)
```

Но при этом `Review.reviewer_id` и `reviewee_id` на `User` идут через `RESTRICT`, 
то есть пользователей удалять нельзя, если отзывы уже существуют.


### G. `User -> SupportTicket` - это исторически важная, но не “delete-orphan child” связь.

Почему:
- `SupportTicket.user_id` -> `users.id` с `ondelete="RESTRICT"`
- тикет — часть истории поддержки.

Мысленно:
```
User
  └─ SupportTicket   (история поддержки, не удалять каскадом)
```

## “мягкая ссылка”

### H. `Item -> subcategory` - мягкая ссылка

Почему:
`subcategory_id` -> `categories.id` с `ondelete="SET NULL"`

Смысл:
- если подкатегория исчезнет, вещь не обязана исчезнуть;
- можно просто обнулить subcategory_id.

Мысленно:
```
Item
  └─ subcategory_id -> Category
       if deleted -> NULL
```

## I. `Item -> moderated_by_admin_id` - мягкая ссылка

Почему:
- `moderated_by_admin_id` -> `users.id` с `ondelete="SET NULL"`

Смысл:
- запись о модерации может остаться, даже если конкретный admin-user исчезнет из ссылки.

## J. `User -> banned_by_admin_id`

То же самое:
- `banned_by_admin_id` -> `users.id` с `SET NULL`

## Вообще нет FK-родителя

### K. `AdminAction` - стоит особняком.

Почему:
- у него `admin_id` хранится просто как `BigInteger`;
- это не FK на `users.id`

Смысл:
- audit log не зависит от ORM-связи с `User`;
- он хранит внешний идентификатор админа как значение.

Мысленно:
```
AdminAction
  └─ admin_id/admin_tg_id   (значение, а не ORM-родительская связь)
```

## Карта именно “по типам связей”

### Настоящие parent-child
- `User -> Item`
- `Item -> Photo`
- `Category -> subcategories`
- `Rental -> Review`

### История / RESTRICT
- `Item -> Rental`
- `User -> Rental`
- `User -> Review`
- `User -> SupportTicket`

### Мягкие ссылки / SET NULL
- `Item -> subcategory`
- `Item -> moderated_by_admin_id`
- `User -> banned_by_admin_id`

### Без FK-связи
- `AdminAction.admin_id/admin_tg_id`


## Простым языком

Когда смотришь на новую связь в модели, задавай 3 вопроса:

### 1. Может ли сущность жить без родителя?

Если нет, это parent-child.

Примеры:
- `Photo` без `Item` — нет
- `Item` без `User` в твоей модели — нет

### 2. Это история, которую нельзя терять?

Если да, скорее всего `RESTRICT`.

Примеры:
- `Rental`
- `Review`
- `SupportTicket`

### 3. Это просто дополнительная ссылка?

Если да, возможен SET NULL.

Примеры:
- `subcategory_id`
- `moderated_by_admin_id`

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


### **ForeignKey("users.id", ondelete="RESTRICT")**

❌ Запрещает удалить строку из users, если на неё есть ссылки в этой таблице

- RESTRICT = «не трогай, если есть история»   (История / финансы / сделки)
- CASCADE = 🔥 удаляет всё связанное	(временные данные)
- SET NULL	= ставит NULL	мягкие связи (мягкие связи)
- NO ACTION	= зависит от БД	редко

### **Два разных механизма создания индексов**
- mapped_column(..., index=True)
- __table_args__ = (Index("ix_xxx_field", "field"))

Если оставить оба:
* SQLAlchemy создаст ДВА индекса
* один с автогенерированным именем
* второй с явным именем

👉 Это непрофессионально и ведёт к мусору в БД.

*Решение - не используем index=True*
*Вместо него - __table_args__ = Index()

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