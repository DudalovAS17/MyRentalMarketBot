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
