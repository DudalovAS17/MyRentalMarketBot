# Rental

### По Законам репозиториев
- `get_*` → обычно один объект
- `list_*` → коллекция

---

- `.all()` - уже возвращает list, так что list(...) лишний шум. Меняем везде
- `list(res.scalars().all()) -> res.scalars().all()`. Но мы не меняем, 
т.к. будет подчеркивание из-за **Expected type 'list[Rental]', got 'Sequence[Any]' instead**
- `.order_by(Rental.created_at.desc())` - по дате создания. Последние сделки по вещи (для проверки открытых аренд)
- `.order_by(desc(Rental.id))` - по убыванию id
- `.order_by(Rental.created_at.desc(), Rental.id.desc())` - Более надёжный вариант: 
основной порядок — по бизнес-смыслу (created_at), вторичный — детерминизм (id).
- `.where(Rental.id == rental_id)` - обновляем конкретную сделку
- `.limit(10)` - берём небольшой хвост, фильтруем в сервисе

---
### Борьба с подчеркиванием строчки `res.rowcount > 0`
`rowcount`  — это “сколько строк затронул UPDATE/DELETE”
- `0` → ничего не обновили (условия WHERE не совпали)
- `>0` → обновили хотя бы одну строку
- `иногда бывает -1` → “драйвер не знает/не сообщает” (редко, но возможно)
- также бывает, что атрибута вообще нет (по typing PyCharm), но в рантайме обычно есть.

1) `return (res.rowcount or 0) > 0` 
- True/False (None → 0, 0 → 0, 1 → 1)
- Была ли реально изменена хотя бы одна строка?
  - True → изменение произошло (владелец подтвердил передачу)
  - False → ничего не изменилось

*Не помогло - подчеркивает.*
2) 
```
updated_rows = int(getattr(res, "rowcount", 0) or 0)
return updated_rows > 0
```
- `getattr(res, "rowcount", 0)`
  - если у res есть .rowcount → берём его значение
  - если нет → берём 0

*То есть будет чем-то вроде: 0, 1, 2, -1, или 0 по умолчанию.*

`updated_rows > 0`
- True 1,2,3,..
- False 0 и отриц-е

---
### Разбор функции try_update_status()
```
async def try_update_status(...) -> bool:
    """Обновляем статус сделки"""

    ...

    async with self._sf() as s:
        stmt = (
            update(Rental)
            .where(Rental.id == rental_id)
            .where(actor_col == actor_user_id) 
            .where(Rental.status == expected_status)
            .values(status=new_status)
        )
        res = await s.execute(stmt)
        await s.commit()
        return (res.rowcount or 0) > 0
```
  
### О строчке `.where(actor_col == actor_user_id)`:
`getattr(Rental, actor_field)` превращается в: `Rental.owner_id` или `Rental.renter_id`, 
получим либо `WHERE owner_id = :actor_user_id`, либо `WHERE renter_id = :actor_user_id`. 
Следствие: **[пользователь физически не может изменить чужую сделку]()**
- даже если хендлер ошибся
- даже если кто-то подменит callback_data

### О строчке `.where(Rental.status == expected_status)`:
Пример:
- два человека нажали “Подтвердить”
- первый → статус стал CONFIRMED
- второй → WHERE status = REQUESTED уже не выполняется rowcount = 0

*Это защита от двойных кликов, устаревших кнопок, гонок (две кнопки нажали — обновится только один раз)*

**[❗ Никаких “случайных” повторных подтверждений.]()**
      
### О строчке `(res.rowcount or 0) > 0`
`res.rowcount` — сколько строк реально изменено
- True → статус действительно изменён
- False → не та роль / не тот статус / сделки нет / кнопка устарела

Сервис решает, что с этим делать (кинуть ошибку, показать alert).

---

### `list_user_rentals()`

```
dto = RentalOut.model_validate(r, from_attributes=True)
result.append(RentalWithRoleOut(**dto.model_dump(), user_role=user_role))
```

- r — ORM объект SQLAlchemy (Rental)
- RentalOut — Pydantic DTO с полями сделки (id, item_id, status, start_date…)
- RentalWithRoleOut — расширенный DTO: всё как RentalOut + user_role

### `dto = RentalOut.model_validate(r, from_attributes=True)`
- преобразование ORM → DTO (Pydantic-модель)

Без `from_attributes=True` Pydantic по умолчанию ожидает mapping/dict-like вход 
(или модель/объект, который он умеет превращать в dict). ORM-объект — не dict.

✅ `from_attributes=True` включает режим: читай поля через `getattr(obj, field_name)`.

### ```result.append(RentalWithRoleOut(**dto.model_dump(), user_role=user_role))```

Тут две идеи:
- взять все поля сделки из dto
- добавить одно поле user_role

`dto.model_dump()` — Это Pydantic v2 способ получить словарь полей DTO.

`**dto.model_dump()` ** — это распаковка словаря в именованные аргументы функции.

```
То есть:
RentalWithRoleOut(**dto.model_dump(), user_role=user_role)

эквивалентно:
RentalWithRoleOut(
  id=dto.id,
  renter_id=dto.renter_id,
  owner_id=dto.owner_id,
  status=dto.status,
  created_at=dto.created_at,
  ...,
  user_role=user_role
)
```

[`RentalWithRoleOut(...)` = новый Pydantic объект (чистый + user_role)
]()

---

### `create_rental()`

Сервис создал аренду → handler решает, отправлять ли уведомление и какую клавиатуру прикладывать.

- `owner_id` (в rental) = db_user_id
- `telegram_id` (в User) = Telegram ID, по нему и отправляем.

Мы ушли от details = {} как dict, к
```
RentalDetailsOut(
    id=rental.id,
    rental=RentalOut.model_validate(rental),
    item=ItemOut.model_validate(item),
    renter=UserOut.model_validate(renter),
    owner=UserOut.model_validate(owner),
    user_role=role
)
```

единственное, что он не учитывает: “Неизвестный товар”, “-”, 0 — это UI-дефолты.
✅ По Законам такие дефолты должны быть:
- в handler (UI слой)
- в helpers/formatters

Там это будет примерно так:
```
      item_title = details.item.title or "Неизвестный товар"
      item_desc = details.item.description or "-"
      location = details.item.location or "-"
      
      owner_name = details.owner.full_name or "-"
      renter_name = details.renter.full_name or "-"
```

### `confirm_requested()`

    ok=True  →  статус реально сменился в базе (1 строка обновлена)
    ok=False →  ничего не изменилось (0 строк обновлено), значит:
                - либо статус уже не REQUESTED,        
                - либо rental_id не существует,        
                - либо owner_id не совпал (не тот актёр).        
    И сервис превращает это в понятную ошибку.


###  Тут пока остановился
    ====== ADMIN MANAGEMENT — админка ======