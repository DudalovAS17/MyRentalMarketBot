# Repository

---
* logger.info("create() — тикет успешно создан, id=%s", obj.id)
* logger.error("create() — ошибка при создании тикета: %s", e, exc_info=True)
* logger.warning("update() — тикет id=%s не найден", ticket_id) 
* logger.info("update() — изменений для тикета id=%s нет", ticket_id) 
* logger.info("update() — тикет id=%s успешно обновлён", ticket_id) 
* logger.error("update() — ошибка при обновлении тикета id=%s: %s", ticket_id, e, exc_info=True)
