# Repository

---
* logger.error("create() Ошибка при создании пользователя: %s", obj.telegram_id, e, exc_info=True)
* logger.info("Создан пользователь id=%s telegram_id=%s username=%r", obj.id, obj.telegram_id, obj.username)
* logger.warning("update() — пользователь с id=%s не найден", user_id)
* logger.error("Ошибка при обновлении пользователя %s: %s", user_id, e, exc_info=True)
* logger.info("Обновлён пользователь id=%s", obj.id)
* logger.warning("delete() — пользователь с id=%s не найден", user_id)
* logger.info("delete() — пользователь id=%s успешно удалён", user_id)
* logger.error("delete() — ошибка при удалении пользователя id=%s: %s", user_id, e, exc_info=True)
---

# Service

## `register_user()`

`UserUpdate(**user_data.model_dump(exclude_unset=True))` - мы создаём объект UserUpdate с теми же данными, 
что и в UserCreate



                
            