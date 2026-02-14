# Repository
```
class CategoryRepository:
    """Репозиторий для Category.
    Создаёт и закрывает сессию в каждом методе
    DI: session_factory -> AsyncSession (новая сессия на каждый вызов)"""
```
---

### Вопрос по create() - это убрал, но смысл вроде есть
```
except Exception:
    await s.rollback()
    # дубликат по (parent_id, name) — вернём существующую
    existing = get_by_name_within_parent(name, parent_id)
    if existing:
        logger.warning(
            "category duplicate → return existing (parent_id=%s, name=%r, id=%s)",
            parent_id, name, existing.id,
        )
        return existing
```
---

```
async def list_all(self) -> List[Category]:
    """Получает все категории (с подкатегориями)"""
    async with self._sf() as s:
        res = await s.execute(select(Category))
        return list(res.scalars())
```

- `stmt = select(Category)` - построили SQL запрос: дай все колонки из таблицы categories
- `result = await s.execute(stmt)` - отправили запрос в БД. Получим кортеж из одного элемента (ORM-объекта):

``list(result)[:2] даст [(<Category id=1>,), (<Category id=2>,), ...]``

- `rows = result.scalars()` - убрали лишнюю обёртку-кортеж, теперь это итератор. Из результата вытаскиваем не кортежи колонок, а сами ORM-объекты Category
- `categories = list(rows)` - материализуем итератор в список categories:

`[<Category id=1>, <Category id=2>, <Category id=3>]`

- `return categories`  - вернули


```
data = update_data.model_dump(exclude_unset=True)
if not data:
    return obj  # изменений нет — просто возвращаем текущий объект
```

---

- `.where(Category.parent_id.is_(None))` - parent_id = NULL
- `.order_by(Category.name)` - сортируем по имени, чтобы в UI было стабильно и красиво (алфавит)
- `return await s.get(Category, category_id)` - дай мне категорию с таким id (select(...).where(...) можно и так)


``` get_by_name_within_parent()
cond = and_(
    Category.name == name,
    Category.parent_id.is_(None)
    if parent_id is None
    else Category.parent_id == parent_id, 
)
res = await s.execute(select(Category).where(cond))
return res.scalar_one_or_none()
```
- `Category.name == name` - точное совпадение имени
- `if parent_id is None` → ищем среди категорий, `else Category.parent_id == parent_id` → ищем среди подкатегорий внутри указанной категории
- `select(Category).where(cond)` - выбрать строки из таблицы categories, где выполняется условие cond
- `res.scalar_one_or_none()` - вернёт объект Category, если нашли ровно одну строку, вернёт None, если не нашли


---

- `name.strip()` - убираем пробелы по краям

---
* logger.info("category created id=%s name=%r parent_id=%s", obj.id, obj.name, obj.parent_id)
* logger.error("category create failed (parent_id=%s, name=%r): %s", parent_id, name, e, exc_info=True)
*               
* logger.info("category not found for update (id=%s)", category_id)
* logger.warning(category update conflict (id=%s, new_name=%r): %s", category_id, name, e) 
* logger.info("category updated id=%s", obj.id)
* logger.info("category not found for delete (id=%s)", category_id)
* logger.error("category delete failed (id=%s): %s", category_id, e, exc_info=True)
* logger.info("category deleted id=%s", category_id)

---

# Service

1. ### list_main
`list_roots()` приходит в виде: `[<Category id=1 name="Электроника" parent_id=None>, <Category id=2 name="Одежда" parent_id=None>]`

Это не словари, а Python-объекты SQLAlchemy

`return [CategoryOut.model_validate(c) for c in cats]` даст → `[CategoryOut(id=1, name="Электроника", ...), CategoryOut(id=2, name="Одежда", ...)]` ← Pydantic-модели

~~Было ранее: `return [c.to_dict() for c in cats]` - DictMixin (объект модели в словарь (берёт все колонки таблицы)). 
Итог получали: `[{"id": 1, "name": "Электроника", "parent_id": None},{"id": 2, "name": "Одежда", "parent_id": None}]`~~

2. Было:
- `list_main`: `[c.to_dict() for c in subs]`
- `list_subcategories`: `[s.to_dict() for s in subs]`
- `get_category`: `cat.to_dict() if cat else None`
- `create`: `obj.to_dict() if obj else None`

И во всех: `-> Dict[str, Any]`