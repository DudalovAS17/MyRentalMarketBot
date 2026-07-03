# Notification — тексты уведомлений

Формируют единый UX: тексты уведомлений.

## 1. Карта файлов

| Файл                       | Назначение                                                                 |
|----------------------------|----------------------------------------------------------------------------|
| `handlers/notification.py` | Форматирование уведомлений о заявках, статусах аренды и поддержке.         |
| `handlers/admin/notify.py` | Низкоуровневая рассылка уведомлений администраторам по списку Telegram ID. |


## 2. `handlers/notification.py`

Файл содержит чистые функции форматирования. Они не отправляют сообщения сами, а только возвращают HTML-текст для `NotificationService` и handler-слоя.

Основные группы:

### Заявки на аренду

- `format_new_rental_request(details)` — уведомление администраторам о новой заявке;
- `format_user_rental_created(details)` — подтверждение клиенту после создания заявки;
- `format_user_rental_status_changed(details, old_status=None)` — уведомление клиенту о смене статуса;
- `format_client_cancelled_rental(details)` — уведомление о клиентской отмене.

### Поддержка

- `format_new_support_ticket(ticket, user)` — уведомление администраторам о новом тикете;
- `format_user_support_created(ticket)` — подтверждение клиенту;
- `format_support_reply(ticket, reply_text)` — ответ администратора клиенту;
- `format_support_closed(ticket)` — уведомление о закрытии тикета.

### Вспомогательные функции

- `safe(value, default="—")` — безопасное отображение пустых значений;
- `format_datetime(dt)` — единый формат даты/времени;
- `rental_id(details)` — получение ID заявки из DTO разных типов.

---

## 3. `handlers/admin/notify.py`

`notify_admins(bot, admin_ids, notification_text, ticket_id)` — низкоуровневая функция отправки сообщения администраторам. В актуальной логике основная отправка уведомлений вынесена в `NotificationService`, но helper остаётся полезным для точечных сценариев.

---

## 4. Заметка

При добавлении нового события уведомления сначала добавить formatter, потом метод в `NotificationService`, 
и только после этого вызывать его из handler/service flow.