# Что такое `strict`
`strict` — это флаг режима строгости метода.

Определяет, как сервис должен себя вести, если объект не найден:
- мягко вернуть пустой результат
- или считать это ошибкой сценария и выбросить исключение

### Если `strict=False`
Метод работает **мягко**:
- если объект не найден → возвращает `None` или `False`
- исключение не выбрасывается

Пример:
- `category = await category_service.get_category(123, strict=False)`
- [Если категории нет](), результат будет `None`


### Если `strict=True`

Метод работает **жёстко**:
- если объект не найден → выбрасывает доменное исключение (например `NotFoundError`)

Пример
- `category = await category_service.get_category(123, strict=True)`
- [Если категории нет](), будет [не]() `None`, а [**ошибка**]().

### Зачем это нужно
Один и тот же сервисный метод можно использовать в двух разных сценариях.

#### 1. Отсутствие объекта допустимо
Тогда удобно вернуть:
- `None`
- или `False`

и дальше уже вызывающий код сам решит, что делать.

#### 2. Отсутствие объекта — это уже ошибка сценария
Тогда удобно сразу выбросить:
- `NotFoundError`
- или другое доменное исключение

и не писать одну и ту же проверку вручную каждый раз.

---

# Category

[**Сервис для работы с категориями и подкатегориями**]()

### Методы:

>`__init__`
   * `CategoryRepository`

>`list_main_categories` - Возвращает все категории без подкатегорий (parent_id = NULL)

> `list_subcategories` - Возвращает все подкатегории для категории `category_id`
  * Если `strict=False`:
    - просто возвращает список подкатегорий
  * Если `strict=True`:
    - сначала проверяет существование родительской категории `->` возвращает список подкатегорий
    - если категория не найдена, выбрасывает `NotFoundError`

>`strict=False`: если вернулся пустой список `[]`, ты не знаешь, что это значит:
>* либо категория существует, но у неё просто нет подкатегорий
>* либо категории с таким `id` вообще нет
>
>Для нестрогого режима это нормально.

>`strict=True`: ты сначала говоришь:
>* “родительская категория обязана существовать”
>* если её нет — это ошибка, а не просто пустой результат
>
>И только потом уже читаешь подкатегории.

> `get_category_by_id` - Возвращает категорию по её `id`
  * `strict`

> `create` - Создаёт категорию или подкатегорию
  * Принимает: `name` и `parent_id`

> `update` - Обновляет категорию или подкатегорию
  * Принимает: `category_id` / `name` / `emoji`
  * `strict`

> `delete` - Удаляет категорию или подкатегорию
  * `strict`

---

# Item

[**Сервис для работы с объявлениями**]()

Прим. `active_only=available_only` - в репо это превратиться в требование через `ItemStatus.ACTIVE`
  (то есть это не `is_available`)

### Методы:

>`__init__`
   * `ItemRepository`
   * `RentalService`

>`list_all_items` - [Возвращает список объявлений]()
  * По умолчанию: только доступные (`available_only=True`)
  * Поддерживает: `limit` и `offset`

>`get_item_by_id` - [Возвращает объявление по его `id`]()
  * `strict`

>`list_by_user` - [Возвращает все объявления пользователя `user_id`]()
  * `available_only=False` по умолчанию
  * Если `available_only=True`: возвращает только активные объявления пользователя

>`list_by_category` - [Возвращает все объявления категории `category_id`]()
  * По умолчанию: только доступные (`available_only=True`)

>`list_by_subcategory` - [Возвращает все объявления подкатегории `subcategory_id`]()
  * По умолчанию: только доступные (`available_only=True`)

>`search` - [Поиск объявлений по названию / описанию]()
  * Принимает: `query` / `available_only` / `limit` / `offset`

>`create` - [Создаёт новое объявление]()
  * Принимает: `user_id` и `item_data: ItemCreate`

>`update` - [Обновляет объявление]()
  * Принимает: `item_id` и `update_data: ItemUpdate`
  * `strict`

>`delete` - [Удаляет объявление]()
  * `strict`

### For Admins-only функции:

>`admin_list_pending` - [Возвращает список объявлений со статусом `PENDING`]()
  * Это объявления на модерации
  * Работает через `admin_list_by_status`

>`admin_list_by_status` - [Возвращает список объявлений по статусу с пагинацией]()
  * Принимает:`status` и `page`
  * Внутри: `page_size = 8`!
  * Возвращает: список объявлений текущей страницы и `has_next`

>`moderate_set_status` - [Меняет статус объявления админом с бизнес-проверками]()
  * Принимает: `item_id` / `new_status` / `admin_id` / `reason` / `strict`

>* Сначала получает текущее объявление
>* Если объявления нет:
>  - `strict=False` → возвращает `None`
>  - `strict=True` → выбрасывает `NotFoundError`
>
>* Потом проверяет допустимость перехода статуса:
>  - через `can_transition(old_status, new_status)`
>
>* Если переход запрещён:
>  - `strict=False` → возвращает `None`
>  - `strict=True` → выбрасывает `ConflictError`
>
> ТОЛЬКО при скрытии объявления возникает риск сломать активную сделку, поэтому:
>* Отдельная бизнес-проверка для `ItemStatus.HIDDEN`:
>  - нельзя скрыть объявление, если по нему есть открытые сделки!
>  - для этого сервис вызывает `rental_service.has_open_rentals_for_item(item_id)`
>
>* Если всё допустимо:
>  - вызывает `item_repo.set_status(...)`
>  - `if not updated:` - теоретически `item` мог исчезнуть между `get_by_id` и `set_status`
>  - логирует смену статуса
>  - возвращает `ItemOut`

P.S. раньше в этой функции была зависимость от репо, а не сервиса Rental:
- `rental_repo: RentalRepository`
- `self.rental_repo = rental_repo`
- `has_open = await self.rental_repo.has_open_rentals_for_item(item_id)`

Заменили на `RentalService`: теперь `ItemService` больше не знает про `RentalRepository`.


---

# Rental

[**Сервис для работы со сделками аренды**]()

### Методы:

>`__init__`
   * `RentalRepository`
   * `NotificationService`?

### Read methods:

> `get_by_id` - [Возвращает сделку по её `id`]()
  * `strict`

> `list_rentals_by_user` - [Возвращает все сделки, где пользователь `user_id` участвует как арендатор или владелец]()

> `list_rentals_by_renter` - [Возвращает все сделки, где пользователь `renter_id` является арендатором]()

> `list_rentals_by_owner` - [Возвращает все сделки, где пользователь `owner_id` является владельцем]()

> `list_user_rentals` - [Возвращает все сделки пользователя с указанием его роли в каждой сделке]()
  * Определяется роль (через `RentalActorRole`)
  * Возвращает `RentalWithRoleOut`

> `get_rental_details` - [Возвращает полную информацию о сделке]()
  * Принимает: `rental_id` / `current_user_id` / `strict`
  * Загружает: саму сделку / `item` / `renter`  / `owner`
  * Доступ разрешён только: арендатору и владельцу
  * Возвращает `RentalDetailsOut`

### CRUD methods:

> `create` - [Создаёт новую сделку]()
  * Принимает: `data: RentalCreate`

> `update` - [Обновляет сделку]()
  * Принимает: `rental_id` и `data: RentalUpdate`
  * `strict`

> `delete` - [Удаляет сделку по её `id`]()
  * `strict`

### Status management — ядро бизнес-логики:

> `_transition` - [Внутренний метод смены статуса сделки]()
  * Принимает: `rental_id` / `actor_user_id` / `actor_role` / `expected_status` / `new_status` / `strict` / `err_msg`
  * Вызывает `rental_repo.try_update_status(...)`
  * Логирует переход статуса

> `confirm_requested` - [Переводит сделку `REQUESTED -> CONFIRMED`]()
  * Выполняет только владелец

> `reject_requested_by_owner` - [Переводит сделку `REQUESTED -> REJECTED_BY_OWNER`]()
  * Выполняет только владелец

> `reject_requested_by_renter` - [Переводит сделку `REQUESTED -> REJECTED_BY_RENTER`]()
  * Выполняет только арендатор

> `cancel_confirmed_by_owner` - [Переводит сделку `CONFIRMED -> CANCELLED_CONFIRMED_BY_OWNER`]()
  * Выполняет только владелец

> `cancel_confirmed_by_renter` - [Переводит сделку `CONFIRMED -> CANCELLED_CONFIRMED_BY_RENTER`]()
  * Выполняет только арендатор

> `start_rental` - [Переводит сделку `CONFIRMED -> ACTIVE`]()
  * Сейчас выполняется владельцем
  * По комментарию в коде: в будущем может стартовать автоматически по дате

> `complete_active` - [Переводит сделку `ACTIVE -> COMPLETED`]()
  * Сейчас выполняется владельцем

> `cancel_active_by_owner` - [Переводит сделку `ACTIVE -> CANCELLED_BY_OWNER`]()
  * Выполняет только владелец

> `cancel_active_by_renter` - [Переводит сделку `ACTIVE -> CANCELLED_BY_RENTER`]()
  * Выполняет только арендатор

> `open_dispute` - [Переводит сделку `ACTIVE -> DISPUTED`]() - стиль немного отличается от всех остальных выше
  * Спор может открыть участник сделки
  * Проверка идёт через `try_update_status_if_participant(...)`
  * `strict`

### Admin-Rental logic:

> `_get_open_rental_for_item` - [Внутренний метод]()
  * Возвращает ORM-модель аренды или `None`
  * Нужен для доменной логики внутри сервиса
  * Наружу ORM не отдаётся

> `get_open_rental_for_item` - [Возвращает первую открытую аренду для объявления `item_id`]()
  * Если открытой аренды нет: возвращает `None`
  * Если есть: возвращает `RentalOut`

> `ensure_item_available` - [Доменная гарантия, что вещь можно арендовать]()
  * Проверяет, есть ли открытая аренда для `item_id`
  * Тут для доменной проверки лучше работать с моделью БД `Rental` (без Pydantic-валидации `RentalOut`), 
    это быстрее и проще, и меньше шансов на “почему `end_date` не того типа”

### Сценарий передачи / получения вещи

> `confirm_handover_by_owner` - [Владелец подтверждает передачу вещи]()
  * Работает только для сделки в `CONFIRMED`
  * После успешного подтверждения: пытается активировать аренду 

> `confirm_receive_by_renter` - [Арендатор подтверждает получение вещи]()
  * Работает только для сделки в `CONFIRMED`
  * После успешного подтверждения: пытается активировать аренду

Тут точно `ConflictError`? (в обеих)

### Еще

> `has_open_rentals_for_item` - [Возвращает `True`, если у объявления `item_id` есть открытые сделки]()
  * Используется, чтобы убрать зависимость от rental_repo: `RentalRepository` в сервисе `Item`

---

# User

[**Сервис для работы с пользователями**]()

### Есть `use-case/user.py`

Цель добавления: решает, [что делать при входе пользователя в `/start`]()

### Методы:

>`__init__`
   * `UserRepository`
   * `admin_ids: FrozenSet[int]`

>`_is_admin` - [Проверяет, входит ли `tg_user_id` в whitelist администраторов]()

>`get_by_id` - [Возвращает пользователя по его `id`]()
  * `strict`

>`get_by_telegram_id` - [Возвращает пользователя по его `telegram_id`]()
  * `strict`

>`list_all` - [Возвращает всех пользователей]()

> `create` - [Создаёт нового пользователя]()
  * Принимает: `user_data: UserCreate`

> `update` - [Обновляет данные пользователя]()
  * Принимает: `user_id` / `update_data: UserUpdate`
  * `strict`

> `delete` - [Удаляет пользователя]()
  * `strict`

>`register_or_update_user` - [Регистрирует пользователя или обновляет существующего по `telegram_id`]()
  * Если пользователь уже существует: обновляет его через `UserUpdate(**payload)`
  * Если пользователь не существует: создаёт нового пользователя
  * Если update/create не удалось: выбрасывает `ServiceError`

### For Admins-only функции:

> `ban_user` - [Банит пользователя с записью причины]()
>* Принимает: `user_id` / `admin_user_id` / `reason` / `strict`
>* Проверяет, что админ не пытается забанить самого себя
>* Проверяет, что пользователь существует
>* Проверяет, что пользователь не является администратором
>* Проверяет допустимость перехода:
>  - `current_status -> AccountStatus.BANNED`
>  - через `can_transition(...)`
>* Формирует `UserAdminUpdate`:
>  - `account_status = BANNED`
>  - `banned_at = datetime.now(timezone.utc)`
>  - `banned_by_admin_id = admin_user_id`
>  - `ban_reason = reason`
>* После этого обновляет пользователя и возвращает `UserOut`

> `unban_user` - [Разбанивает пользователя]()
>* Принимает: `user_id` / `strict`
>* Проверяет, что пользователь существует
>* Проверяет допустимость перехода:
>  - `current_status -> AccountStatus.ACTIVE`
>  - через `can_transition(...)`
>* Формирует `UserAdminUpdate`:
>  - `account_status = ACTIVE`
>* После этого обновляет пользователя и возвращает `UserOut`

>`check_user_exists` - [Проверяет, существует ли пользователь с данным `telegram_id`]()

>`is_user_blocked` - [Проверяет, заблокирован ли пользователь с данным `telegram_id`]()
  * `strict`

>`resolve_start_entry` - [Решает, что делать при входе пользователя в `/start`]()
  * Если пользователь не найден: `StartAction.REGISTER`
  * Если пользователь найден, но `account_status != ACTIVE`: `StartAction.ACCESS_BLOCKED`
  * Если пользователь активен: `StartAction.MAIN_MENU`
  * Возвращает `StartEntryResult`

---

# AdminAction

[**Сервис для записи административных действий в журнал аудита**]()

### Методы:

>`__init__`
   * `AdminActionRepository`

>`log_action` - [Записывает действие администратора в audit-журнал]()
>* Принимает: `admin_tg_id` / `action_type` / `entity_type` / `entity_id` / `note` / `payload`
>* `action_type` и `entity_type` могут прийти как `str` или `enum.Enum`
>
>* Если приходит `Enum`: сервис берёт `.value`
>* Если приходит `str`: сервис приводит значение через `str(...)`
>
>* `entity_id` всегда приводится к строке:
>  - это делает контракт записи единообразным
>  - неважно, пришёл `int` или `str`
>
>* После нормализации сервис:
>  - вызывает `AdminActionRepository.create(...)`
>  - получает ORM-объект audit-записи
>  - преобразует его в `AdminActionOut`

---

# AdminRental

[**Админский сервис для управления сделками и административного вмешательства в их жизненный цикл**]()

### Методы:

>`__init__`
   * `RentalRepository`
   * `AdminActionService`

#### Read methods:

>`list_recent_rentals` - [Возвращает последние сделки для админского экрана с пагинацией]()
  * `limit N` - Верни не больше `N` строк (сколько записей вернуть)
  * `offset M` - Пропусти первые `M` строк, потом начинай возвращать результат (сколько записей пропустить)
  * Принимает: `page`

>`get_details` - [Возвращает полные детали сделки для администратора]()
> * Принимает: `rental_id`
> * `strict`
>* Если сделка найдена: собирает `RentalAdminDetailsOut`

#### Admin override methods:

>`admin_cancel_rental` - [Принудительно отменяет сделку администратором]()
>
>Эта функция — властное вмешательство платформы в жизненный цикл сделки,
когда нормальные пользовательские сценарии уже не работают или не должны работать.
Это рычаг платформы, а не кнопка пользователя. Может происходить в любой момент.
>
>1) Сделка застряла: арендатор пропал | владелец не отвечает | статус висит неделями
>2) Нарушение правил: фейковое объявление | запрещённый предмет | мошенничество
>3) Спор, который нельзя “разрулить автоматически”
>4) Юридическая/репутационная защита

>* Принимает: `rental_id` / `admin_id` / `reason` / `strict`
>* Это платформенное вмешательство в сделку, а не обычный пользовательский сценарий.
>
>* Сначала сервис получает сделку по `rental_id`
>* `strict`
>
>* Потом проверяет:
>  - не находится ли сделка в терминальном статусе
>  - можно ли вообще отменять сделку из её текущего статуса
>
>* Для этого использует: `TERMINAL_STATUSES` / `CANCEL_STATUS_MAP`
>
>* Если отмена допустима:
>  - обновляет статус сделки через `RentalUpdate(status=...)`
>  - пишет audit-запись через `AdminActionService.log_action(...)`
>  - логирует действие администратора
>  - возвращает `True`

>`admin_resolve_dispute` - [Закрывает спор по сделке и переводит её в разрешённый целевой статус]()
>
> - В карточке сделки (если статус `DISPUTED`) появляется кнопка “✅ Закрыть спор”
> - Админ нажимает `→` бот просит текст решения (FSM)
> - После ввода текста → бот показывает кнопки выбора исхода:
>    * “➡️ Перевести в `ACTIVE`”
>    * “✅ Завершить (`COMPLETED`)”
>    * “↩️ Вернуть в `CONFIRMED`” (если этот статус у тебя есть)
>
>Нажатие кнопки → выполняется изменение статуса только по whitelist-статусам,
пишется audit log, перерисовывается карточка сделки.

>* Принимает: `rental_id` / `admin_id` / `resolution` / `target_status` / `strict`
>
>* Сначала сервис получает сделку по `rental_id`
>* `strict`
>
>* Потом проверяет:
>  - что текущий статус сделки = `DISPUTED`
>  - что `target_status` входит в разрешённый whitelist
>
>* Для этого использует: `ALLOWED_TARGETS`
>
>* Если разрешение спора допустимо:
>  - обновляет статус сделки
>  - пишет audit-запись через `AdminActionService.log_action(...)`
>  - логирует действие администратора (только если изменение реально применилось)
>  - возвращает `True`

---

# Photo

[**Сервис для управления фотографиями объявления**]()

### Методы:

>`__init__`
   * `PhotoRepository`

### Read methods

> `get_photo_by_id` - [Возвращает одну фотографию по её `id`]()

> `get_photos_by_item_id` - Возвращает все фотографии объявления `item_id` (в текущем порядке отображения)

### Write methods

> `create_photo` - [Добавляет одну фотографию к объявлению]() - возможно надо доделать
  * Принимает: `item_id` / `telegram_file_id` / `order`
  * Если `order=None`:
    - сервис сам ставит фото в конец списка
    - для этого считает текущее количество фото у объявления
  * Если `order` передан явно:
    - после добавления выполняет `reorder(item_id)`
    - чтобы порядок остался плотным, без дырок

> `create_photos` - [Добавляет несколько фотографий к объявлению]()
  * Принимает: `item_id` / `file_ids`
  * Если `file_ids` пустой: возвращает `[]`
  * Порядок новых фото назначается “в хвост” (после уже существующих фотографий объявления)

> `delete_photo` - [Удаляет фотографию по её `id`]()
  * После удаления: сервис вызывает `reorder(photo.item_id)`, чтобы уплотнить порядок у оставшихся фотографий

### Order management

> `move_photo` - [Перемещает фотографию вверх или вниз]()
  * Принимает: `photo_id` / `direction: "up" | "down"`
  * Внутри: сначала получает фотографию, затем вызывает `swap_with_neighbor(...)` в repo

> `set_order` - [Устанавливает явный `order` для фотографии]()
  * Принимает: `photo_id` / `new_order`
  * Внутри: сначала получает фотографию, затем вызывает `set_order(...)` в repo

---

# Review

[**Сервис для работы с отзывами и пересчёта рейтинга пользователя**]()

### Методы:

>`__init__`
   * `ReviewRepository`
   * `RentalRepository` - ?
   * `UserRepository` - ?

### Read methods:

>`get_by_id` - [Возвращает один конкретный отзыв по его `id`]()

>`list_reviews_by_rental` - [Возвращает все отзывы, связанные с конкретной сделкой `rental_id`]()

>`list_reviews_about_user` - [Возвращает все отзывы о пользователе `user_id`]()

>`list_reviews_by_user` - [Возвращает все отзывы, оставленные пользователем `user_id`]()

### Write methods:

>`create_review` - [Создаёт отзыв по сделке]()
> 
>Принимает: `actor_id` / `data: ReviewCreate` / `strict`
>
>* Отзыв можно оставить только если сделка существует
>* Отзыв можно оставить только если статус сделки — `COMPLETED`
>* Отзыв может оставить только участник сделки
>* Один пользователь может оставить только один отзыв по конкретной сделке
>
>* Сервис сам определяет, кому оставляется отзыв:
>  - если отзыв оставляет арендатор → `reviewee_id = owner_id`
>  - если отзыв оставляет владелец → `reviewee_id = renter_id`
>
>* После создания отзыва сервис:
>  - логирует создание
>  - пересчитывает рейтинг пользователя, которому оставили отзыв
>
> Валидируем рейтинг - не нужно: уже гарантируется моделью - Field(ge/le)

>`recalculate_user_rating` - [Пересчитывает рейтинг пользователя на основе всех его отзывов]()
>* Получает агрегаты: `avg_rating` / `count`
>* Затем обновляет: `rating` / `rating_count` - в `UserRepository`

Старый код: 
```python
reviews: List[Review] = await self.review_repo.list_by_reviewee_id(user_id)
if not reviews:
    await self.user_repo.update_rating(user_id=user_id,rating=0.0,rating_count=0)
    return

# reviews = [Review(rating=5), Review(rating=4), Review(rating=3),]
total_rating = sum(r.rating for r in reviews) # total = 5 + 4 + 3 = 12
count = len(reviews) # count = 3 - количество отзывов
avg_rating = round(total_rating / count, 1) #  average = 12 / 3 = 4.0 - средний рейтинг пользователя
# round(4.3333, 1) → 4.3 - округляет
```
---

# Support

[**Сервис для работы с тикетами поддержки**]()

### Методы:

>`__init__`
   * `SupportTicketRepository`

### Read methods:

>`get_ticket_by_id` - [Возвращает тикет по его `id`]()

>`list_open_tickets` - [Возвращает список открытых тикетов с пагинацией]()

>`get_open_ticket_by_user` - [Возвращает открытый тикет пользователя `user_id`]()

### Write methods:

>`create` - [Создаёт тикет обращения]()
> 
>Принимает: `ticket_data: SupportTicketCreateInternal`
>* Перед созданием сервис проверяет: есть ли у пользователя уже открытый тикет
>* Если открытый тикет уже существует: выбрасывает `TicketAlreadyOpen`
>* Если открытого тикета нет: создаёт новый тикет

### Admin actions:
>`close_ticket` - [Закрывает тикет обращения]()
  * Принимает: `ticket_id` / `admin_tg_id`

### Service actions
>`mark_admin_replied` - [Помечает, что администратор ответил по тикету]()
  * Принимает: `ticket_id`

---

# NotificationService

[**СЫРОЙ СЕРВИС - БУДУ ПИСАТЬ ЗАНОВО**]()

---

## Общее для всех

### Что использует:
- `xxxRepository`
- `xxxService`
- `xxxOut` / `xxxCreate` / `xxxUpdate`
- `ConflictError` / `NotFoundError` / `ItemNotAvailable` /`ForbiddenError` / `ServiceError`
- `can_transition`
- `xxxStatus`
- `validate_name`
- `is_open_status`
- `enum.Enum`
- `datetime.now(timezone.utc)`
- `AccountStatus`
- `RentalStatus`
- `StartAction`
- `StartEntryResult`
- `AdminActionType`
- `AdminEntityType`
- `TERMINAL_STATUSES` / `CANCEL_STATUS_MAP` / `ALLOWED_TARGETS`
- `TicketAlreadyOpen`

### Возвращает:
- `xxxOut`
- `Optional[xxxOut]`
- `list[xxxOut]`
- `tuple[list[xxxOut], bool]`
- `bool` / `Optional[bool]`
- ORM-модель аренды (`_get_open_rental_for_item`) — только внутренне
- `StartEntryResult`
- `None`

### return
- `[xxxOut.model_validate(i) for i in xxxs]`
- `xxxOut.model_validate(xxx)`
- `[xxxOut.model_validate(i) for i in xxxs[:page_size]], has_next`
- `RentalWithRoleOut(**dto.model_dump(), user_role=user_role)`
- `await self.repo.exists_by_telegram_id(telegram_id)`
- `user.account_status == AccountStatus.BANNED`
- `StartEntryResult(action=StartAction.REGISTER)`
- `rows, has_next`
- `RentalAdminDetailsOut(...)`
- `True`
- `False`
- `[]`
- `list[PhotoOut]`
- `bool`
- `ok`