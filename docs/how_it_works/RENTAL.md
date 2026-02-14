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

