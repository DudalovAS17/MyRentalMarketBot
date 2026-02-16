# Repository

```
stmt = stmt.limit(limit).offset(offset)
```

- `limit` - возьми не больше n строк
- `offset` - пропусти k первых строк и начинай отдавать дальше

`.where(or_(Item.title.ilike(q), Item.description.ilike(q)))` - по названию ИЛИ описанию. Примеры: "ноут" найдёт и "Ноутбук", и "НОУТ"

`.order_by(Item.id.desc())` - по убыванию id ?

---

* logger.error(f"[ItemRepository] Ошибка при получении всех объявлений: {e}")
* logger.error(f"[ItemRepository] Ошибка при получении объявления {item_id}: {e}")
* logger.error(f"[ItemRepository] Ошибка при получении объявлений категории {category_id}: {e}", exc_info=True)

* logger.error("Ошибка при создании объявления: %s", e, exc_info=True)
* logger.info("item created id=%s user_id=%s title=%r", obj.id, obj.user_id, obj.title)
* logger.warning("Объявление с id=%s не найдено для обновления", item_id)
* logger.error("item update failed (id=%s): %s", item_id, e, exc_info=True)
* logger.info("item updated id=%s", obj.id)
* logger.info("item not found for delete (id=%s)", item_id)
* logger.error("item delete failed (id=%s): %s", item_id, e, exc_info=True)
* logger.info("item deleted id=%s", item_id)
* logger.warning("Объявление с id=%s не найдено для модерации", item_id)
* 
* 
* logger.error("item moderation update failed (id=%s): %s", item_id, e, exc_info=True)
* logger.info("item status updated id=%s status=%s", obj.id, obj.status)
            
                
---

`await s.refresh(obj)` - чтобы были server defaults (id/created_at/updated_at)

---

``` ✅
data = update_data.model_dump(exclude_unset=True)
for k, v in data.items(): 
    setattr(obj, k, v) 
```
- `exclude_unset=True` — вернёт только реально переданные поля (удобно для update)
- `data.items()` возвращает пары ключ-значение - ("title", "Новая палатка"), ("price", 2500)
- `setattr(obj, k, v)` - Это аналог: obj.title = "Новая палатка" obj.price = 2500. Но мы делаем это в цикле для любого набора полей

---

# Service

1. 

- `list_all_items()`: `return [ItemOut.model_validate(i) for i in items]` ->
дает: `[{"id": 1, "user_id": 123, "title": "Палатка Tramp", ...}, {"id": 2, ...} ]`  - список
- `get_item_by_id()`: `return ItemOut.model_validate(item) if item else None` ->
дает: `{"id": 1, "user_id": 123, "title": "Палатка Tramp",...}` - не список, а один объект!

Далее смысл понятен:
- `list_by_user()`: `[ {"id": 1, "user_id": 123, ...}, {"id": 5,"user_id": 123, ...} ]`
- `list_by_category()`: `[ {"id": 1,.., "category_id": 1,...}, {"id": 2, ..., "category_id": 1,...}]`
- `list_by_subcategory()`: `[{"id": 1, "title": "Палатка Tramp", "subcategory_id": 101,...}]`



2. Было:
- `list_all_items`: `return [item.to_dict() for item in items]`
- `get_item_by_id`: `return item.to_dict() if item else None`


### `admin_list_by_status()`

`return [ItemOut.model_validate(i) for i in items[:page_size]], has_next`
- `model_validate(i)` — превращает ORM объект в Pydantic-объект (`ItemOut` — Pydantic-схема (DTO))
- `[ItemOut.model_validate(i) for i in items[:page_size]]` = возьми первые 8 Item и преобразуй каждый в ItemOut

Почему так делают? Чтобы наружу (в handlers/API) не отдавать ORM, а отдавать чистые данные, согласованные со схемой.
`items[:page_size]` - первые page_size элементов. `page_size = 8`

### `create(.. item_data: Union[dict, ItemCreate])` -> `item_data: ItemCreate`

Сервис не должен принимать dict из FSM.
Это “телеграм-граница”. В сервис должны приходить только валидированные DTO.

[FSM/handlers → собирают dict → валидируют в ItemCreate → вызывают service.create(ItemCreate)]()

То есть вся часть (включая логирование ошибок структуры):
``` ✅ Ensure input is a validated Pydantic model
        if isinstance(item_data, dict):
            try:
                item_data = ItemCreate(**item_data)
            except ValidationError as e:
                logger.error(f"Validation error while creating ItemCreate: {e}")
                raise ValueError("Invalid item data structure")
```

— должны жить в handler/adapter, не в сервисе.

⚠️ Обрати внимание: я сделал возвращаемый тип ItemOut, а не Optional[ItemOut].
Создание либо удалось → вернули объект, либо ошибка → исключение.
Это профессиональная модель и она сильно упрощает код.


### `delete()`

> strict=True → кидаем NotFoundError
> 
> strict=False → возвращаем False

Этот код 
```
    if not deleted:
        if strict:
            raise NotFoundError(f"Объявление не найдено: id={item_id}")
        return False

    logger.info("Item deleted id=%s", item_id)
    return True
```

можно заменить на:
```
    if not deleted and strict:
        raise NotFoundError(f"Объявление не найдено: id={item_id}")

    if deleted:
        logger.info("Item deleted: id=%s", item_id)
    return deleted
```

### `add_item_photo()`


Это “телеграм-граница”. Сервис должен принимать нормальные типы (int) и не заниматься парсингом.
✅ Парсинг str→int должен быть в handler/adapter.
``` безопасно привести id (часто приходит как строка из телеги)
try:
    item_id = int(item_id)
except (TypeError, ValueError):
    logger.error("add_item_photo() — неверный item_id: %r", item_id)
    return None
```

`-> Optional[Dict[str, Any]` на `-> PhotoOut`


* logger.error("add_item_photo() — ошибка при создании фото для item_id=%s: %s", item_id, e, exc_info=True)
* logger.error("add_item_photo() — не удалось создать фото для item_id=%s", item_id)

### `remove_item_photo()`

``` Сервис должен принимать нормальные типы (int) и не заниматься парсингом.
try:
    photo_id = int(photo_id)
except (TypeError, ValueError):
    logger.error("remove_item_photo() — неверный photo_id: %r", photo_id)
    return False
```

* logger.error("remove_item_photo() — ошибка при удалении photo_id=%s: %s", photo_id, e, exc_info=True)
* logger.warning("remove_item_photo() — фото id=%s не найдено", photo_id)


### `get_item_photos()`

```
try:
    item_id = int(item_id)
except (TypeError, ValueError):
    logger.error("get_item_photos() — неверный item_id: %r", item_id)
    return []
```

### `moderate_set_status()`

Что тут происходит:
- Берём item из БД
   - нет item → `NotFoundError` (если strict) или `None`
- Проверяем, разрешён ли переход статуса
   - запрещён → `ConflictError` (если strict) или `None`
- Если новый статус `HIDDEN` → проверяем, есть ли открытые сделки
   - есть открытые сделки → `ConflictError` или `None`
- Если все проверки прошли → делаем технический update через `repo.set_status`
   - repo вернул `None` (редкий гон) → `NotFoundError` или `None`
- Возвращаем `ItemOut` наружу


Самый главный смысл этой функции - это бизнес-защита:
- нельзя менять статус как попало (whitelist)
- нельзя скрывать, если идёт сделка

Repo не знает эти правила. Он просто “поставь статус и закоммить”.

В handler ты делаешь так:
``` 
    try:
        dto = await item_service.moderate_set_status(
            item_id=item_id,
            new_status=new_status,
            admin_id=admin_tg_id,
            reason=reason,
            strict=True,
        )
    except NotFoundError:
        ... ответить "не найдено"
    except ConflictError as e:
        ... ответить str(e)
```

