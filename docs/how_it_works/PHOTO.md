# Repository

```
#stmt = select(Photo).where(Photo.item_id == item_id).order_by(Photo.order)
stmt = (
    select(Photo)
    .where(Photo.item_id == item_id)
    .order_by(Photo.order.asc(), Photo.id.asc()) # Зачем сортировать ещё и по id?
    # Каждое фото имеет уникальный id — значит, даже если order = 0 у двух фото, порядок всё равно будет строгим.
    # 1) id=5 (order=0)
    # 2) id=12 (order=0)
    # 3) id=9 (order=1)
)
```
---

* logger.info("create() — фото добавлено для item_id=%s", item_id)
* logger.error("create() — ошибка при добавлении фото: %s", e, exc_info=True)
* logger.warning("delete() — фото id=%s не найдено", photo_id)
* logger.info("delete() — фото id=%s удалено", photo_id)
* logger.error("delete() — ошибка при удалении фото id=%s: %s", photo_id, e, exc_info=True)
* 