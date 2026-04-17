## Base

### Нужно фиксить:
#### [типизация довольно широкая: Any, Optional[Any], list[Any]]()
- create / update / delete - либо так obj: Any) -> Any:

---

## Category

### Методы:
- `list_all` - Получает все категории (с подкатегориями)
- `list_roots` - Получает все категории (без подкатегорий) в алфавитном порядке
- `get_by_id` - Получение категории и подкатегории по ID
- `list_subcategories` - Получение подкатегорий для указанной категории
- `get_by_name_within_parent` - Получение категории по имени
    * если `parent_id=None`: найти категорию по имени
    * если `parent_id=X`: найти подкатегорию по имени внутри категории X
  
  (Нужно сделать `name = name.strip()` в сервисе для этой функции)

- `exists_by_name_within_parent` - Проверка [«есть ли такая запись?»]()  Когда нужен просто ответ «есть / нет»

> `create`
  * `parent_id=None`: создать категорию
  * `parent_id=X`: создать подкатегорию в категории X

(Нет этой логики: Дубликаты по `[parent_id, name]` не создаст — вернёт существующую)
> `update` - Переименовать / сменить emoji у категории или подкатегории
  * получает объект
  * если объекта нет — возвращает None
  * меняет только реально изменившиеся поля
  * если изменений нет — возвращает текущий объект без commit
  * если изменения есть — делает commit/refresh
> `delete` - Удалить категорию или подкатегорию
  * Возвращает `True`, если удалили
  * Возвращает `False`, если не нашли/ошибка

(Если удаляешь категорию — её подкатегории тоже уйдут, каскад)

### Примеры запросов:
* `.where(Category.parent_id.is_(None))`
* `.order_by(Category.name)` - сортируем по имени (алфавит)
* `exists().where(cond))`
* `Category(name=name, emoji=emoji, parent_id=parent_id)`
* `and_(
            Category.name == name,
            Category.parent_id.is_(None)
            if parent_id is None
            else Category.parent_id == parent_id,
        )`

### Возвращаются:
- `Category`
- `list[Category]`
- `Optional[Category]`
- `bool`
- не возвращает DTO/Pydantic

---

## Item

### Методы:
- `list_all` - Все объявления (по умолчанию только доступные)
- `get_by_id` - Объявление по ID
- `list_by_user_id` - Все объявления владельца
- `list_by_category` - Получает все доступные объявления по категории
- `list_by_subcategory` - Получает все доступные объявления по подкатегории
- `search` - Поиск объявлений по тексту. По названию ИЛИ описанию

- `exists_by_name_within_parent` - Проверка [«есть ли такая запись?»]()  Когда нужен просто ответ «есть / нет»

- `list_by_status` - Объявления на модерации по статусу, по убыванию id
- `list_pending` - Объявления на модерации - PENDING
- `set_status` - Техническое обновление статуса объявления. Бизнес-проверки выполняет сервис (whitelist).
  * получает объект
  * пишет новый статус
  * ставит moderated_at
  * пишет moderated_by_admin_id
  * по необходимости записывает moderation_reason
  * делает commit/refresh

  Отмечу: `obj.moderated_at = datetime.now(timezone.utc)`

> `create` - Создать объявление

> `update` - Обновить поля объявления (только переданные)
  - [if not obj](): если `item` не найден → None
  - [if not data](): если `patch` пустой → вернуть текущий ORM без commit
    * объект найден
    * пользователь не передал ни одного поля для изменения
    * фактической DB-mutation нет

    В такой ситуации делать `commit()` обычно не нужно, потому что: 
    ты ничего не изменил / транзакционно фиксировать нечего / лишний commit только создаёт шум.

  - [если изменения есть]() → применить и сделать commit_refresh

```
if not data:
    return obj
    
 означает: “объект существует, но изменений нет — возвращаю текущее состояние как есть”.
```

> `delete` - Удалить объявление (`True` — удалено,`False` — не найдено / ошибка)

### Примеры запросов:
* `.where(Item.status == ItemStatus.ACTIVE)`
* `.where(or_(Item.title.ilike(q), Item.description.ilike(q)))` (`q = f"%{query.strip()}%"`)
* `.order_by(Item.id.desc())`

### Возвращаются:
- `Item`
- `list[Item]`
- `Optional[Item]`
- `bool`
- не возвращает DTO/Pydantic

### Уходим от логики is_available:
```
    def _apply_active_filter(stmt):
        return (
            stmt.where(Item.is_available.is_(True))
            .where(Item.status == ItemStatus.ACTIVE) # NEW (Admin logic)
        )
```
- `available_only` -> `active_only` (доступные = активные)

---

## Rental

### Методы:
- `list_all` — Вернуть все сделки
- `get_by_id` — Найти сделку по ID
- `list_by_item_id` — Все сделки по конкретной вещи = Получение аренд по ID вещи
- `list_by_renter_id` — Сделки, где пользователь — арендатор
- `list_by_owner_id` — Сделки, где пользователь — владелец
- `list_by_user_id` — Все сделки, где пользователь — арендатор или владелец
- `list_by_status` — Сделки по статусу
- `get_details_by_id` — Получить сделку по ID [с заранее подгруженными связями]()
  * `item`
  * `renter`
  * `owner`

(Нужен, чтобы сервис сделок не зависел от сервисов объявлений, пользователей и т.д.)

- `list_recent` — Последние сделки (по убыванию `created_at`)
- `list_recent_with_details_for_admins` — Последние сделки для админ-панели [с заранее подгруженными связями]()
  * `item`
  * `owner`
  * `renter`

> `create` - Создать новую сделку

> `update` - Обновить сделку
  * Возвращает `Rental`, если сделка найдена
  * Если `update_data` пустой — возвращает текущий объект без изменений
  * Если сделка не найдена — возвращает `None`

> `delete` - Удалить сделку по `id`
  * Возвращает `True` — удалена 
  * `False` — не найдена

> `try_update_status` - Атомарно обновить статус сделки, если совпали ожидаемый текущий статус и участник, уже проверенные сервисом.
  * Используется, когда право на переход есть только у одного участника:
    * `OWNER`
    * `RENTER`
  * Обновление происходит только если одновременно выполняется:
    * `rental_id` совпал
    * роль соответствует нужному участнику
    * `actor_user_id` совпал с нужным участником сделки
    * текущий статус равен `expected_status`
  * Возвращает `True`, если статус обновлён, иначе `False`

- `rental_id` - какую сделку мы хотим изменить
- `new_status` - переводим в этот статус
- `expected_status` - из какого статуса разрешён переход
- `actor_user_id` - кто нажал кнопку (текущий пользователь)
- `actor_role` - чьё это право (owner/renter)

> `try_update_status_if_participant` - Обновить статус сделки, если пользователь — любой участник сделки
  * Используется для `DISPUTE`, где действие может выполнить и владелец, и арендатор
  * Обновление происходит только если:
    * `rental_id` совпал
    * `actor_user_id` — это `owner_id` или `renter_id`
    * текущий статус равен `expected_status`
  * Возвращает `True`, если статус обновлён, иначе `False`

`try_update_status` и `try_update_status_if_participant` - две функции, которые можно объединить в одну


> `try_set_owner_handover_confirmed` - Владелец отмечает: “передал вещь”
  * Обновление происходит только если:
    * сделка существует
    * `owner_id` совпадает
    * статус сделки = `CONFIRMED`
    * флаг `owner_handover_confirmed` ещё `False`
  * Устанавливает `owner_handover_confirmed=True`
  * Возвращает `True`, если флаг обновлён

> `try_set_renter_confirm_receive` - Арендатор отмечает: “получил вещь”
  * Обновление происходит только если:
    * сделка существует
    * `renter_id` совпадает
    * статус сделки = `CONFIRMED`
    * флаг `renter_receive_confirmed` ещё `False`
  * Устанавливает `renter_receive_confirmed=True`
  * Возвращает `True`, если флаг обновлён

> `try_activate_confirmed_rental` - Перевести сделку из `CONFIRMED` в `ACTIVE`, если обе стороны подтвердили передачу/получение
  * Условия:
    * статус = `CONFIRMED`
    * `owner_handover_confirmed=True`
    * `renter_receive_confirmed=True`
  * Возвращает `True`, если статус переведён в `ACTIVE` (арендатор подтвердил получение)

- `list_recent_open_by_item_id` — Возвращает последние сделки по `item_id`
  * выборка ограничена `_OPEN_RENTAL_LOOKUP_LIMIT`
  * сервис дальше сам выбирает первую `open`-сделку

  Терминал-ть статуса определим позже в сервисе

- `has_open_rentals_for_item` — Техническая проверка: есть ли у `item` открытые сделки
  * считает `open`-статусы через `is_open_status(...)`
  * возвращает `True` / `False`

  Для сервиса объявлений: moderate_set_status()


### Примеры запросов:
* `.order_by(Rental.created_at.desc())`
* `.options(selectinload(Rental.item))` - Подгружает эту связь заранее
* `.order_by(Rental.created_at.desc(), Rental.id.desc())`
* `.where(or_(Rental.owner_id == actor_user_id, Rental.renter_id == actor_user_id))`

* `.where(actor_col == actor_user_id)` - Права проверяются на уровне БД, а не в Python
* `.where(Rental.status == expected_status)` - Это защита от: двойных кликов, устаревших кнопок, гонок
* `.values(status=new_status)` - Если и только если все WHERE совпали → статус обновляется
* `.where(Rental.owner_handover_confirmed.is_(False))`
* `.values(owner_handover_confirmed=True)` - обновляет поле на True
* `.where(Rental.owner_handover_confirmed.is_(True))` - Владелец передал вещь
* `.where(Rental.renter_receive_confirmed.is_(True))` - Арендатор получил вещь


### Возвращаются:
- `Rental`
- `list[Rental]`
- `Optional[Rental]`
- `bool`
- не возвращает DTO/Pydantic


>`obj = Rental(**rental_data.model_dump())`
> 
> `exclude_unset=True` - в `Create` иногда нужно, иногда нет (спроси GPT)

>`renter_id, owner_id, user_id` - все это `db_user_id` (не `telegram_user_id`)

---

## User

### Методы:

- `list_all`- Возвращает список пользователей по возрастанию `id`

- `get_by_id` - Ищет пользователя `id`

- `get_by_telegram_id` - Ищет пользователя `Tg ID`

- `exists_by_telegram_id` - Проверяет, существует ли пользователь с таким `Tg ID`

> create - Создаёт нового пользователя из `UserCreate`

Надо?: Проверка на дубликат по telegram_id (если пользователь уже существует)

> update - Обновляет только переданные поля пользователя через `UserUpdate | UserAdminUpdate` 

> delete - Удаляет пользователя `id`

- `update_rating` - Технически обновляет кеш рейтинга пользователя: `rating` и `rating_count`

  [Для сервиса отзывов - Обновить рейтинг пользователя]()

### Возвращаются:
- `User`
- `list[User]`
- `Optional[User]`
- `bool`
- не возвращает DTO/Pydantic

---

## User

### Методы: