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
