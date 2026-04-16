## Base

### Нужно фиксить:
#### [типизация довольно широкая: Any, Optional[Any], list[Any]]()
- create / update / delete - либо так obj: Any) -> Any:

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

(Дубликаты по `[parent_id, name]` не создаст — вернёт существующую)
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
