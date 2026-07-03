# Support — пользовательская поддержка

Раздел описывает клиентский flow поддержки. Пользователь может создать обращение из команды `/support`, из кнопки поддержки или из карточки заявки на аренду. Администратор отвечает и закрывает тикеты через admin handlers.

---

## 1. Карта файлов

| Файл                                  | Назначение                                                                    |
|---------------------------------------|-------------------------------------------------------------------------------|
| `handlers/support/support.py`         | `support_router`, старт обращения, FSM ввода текста, создание тикета, отмена. |
| `handlers/support/helpers_support.py` | Тексты поддержки, пустые/повторные состояния и кнопка отмены.                 |
| `states/support_ticket.py`            | `SupportStates.waiting_text`.                                                 |
| `handlers/admin/support.py`           | Административная часть поддержки: список, ответ, закрытие.                    |

---

## 2. Точки входа

| Вход                                            | Обработчик                        | Назначение                          |
|-------------------------------------------------|-----------------------------------|-------------------------------------|
| `/support`                                      | `support_start()`                 | Старт поддержки командой.           |
| callback `support:start`                        | `support_start_callback()`        | Старт поддержки кнопкой.            |
| callback `CLIENT_SUPPORT_RENTAL_CB + rental_id` | `support_start_rental_callback()` | Старт поддержки из карточки заявки. |

Все входы приводят к `start_support_flow()`.

---

## 3. Поддержка из карточки заявки

`support_start_rental_callback()` дополнительно проверяет доступ к заявке:

1. парсит `rental_id` из callback;
2. вызывает `rental_service.get_rental_details(rental_id=rental_id, current_user_id=user.id)`;
3. если заявка не найдена или чужая — показывает alert;
4. если доступ есть — запускает `start_support_flow(..., rental_id=rental_id)`.

Так тикет может быть связан с конкретной заявкой на аренду.

---

## 4. Единый старт: `start_support_flow()`

Алгоритм:

1. проверяет открытый тикет пользователя через `support_service.get_open_ticket_by_user(user.id)`;
2. если открытый тикет есть — показывает текст `build_support_already_open_text(ticket_id)` и не создаёт новый;
3. если тикета нет — ставит `SupportStates.waiting_text`;
4. сохраняет `support_rental_id` в FSM;
5. просит пользователя описать проблему и показывает кнопку отмены.

В текущей модели у пользователя может быть только один открытый тикет.

---

## 5. Создание тикета: `receive_support_text()`

Принимает текст в состоянии `SupportStates.waiting_text`.

Обработка:

1. обрезает текст и проверяет, что он не пустой;
2. читает `support_rental_id` из FSM;
3. собирает `SupportTicketCreateInternal`:
   - `user_id=user.id`;
   - `text=text`;
   - `subject="Заявка на аренду #..."`, если тикет связан с заявкой;
   - `rental_id=rental_id`;
4. вызывает `support_service.create(ticket_data=internal)`;
5. при `TicketAlreadyOpen` очищает FSM и показывает сообщение о существующем тикете;
6. при успехе очищает FSM;
7. уведомляет пользователя через `notification_service.notify_user_support_ticket_created()`;
8. уведомляет администраторов через `notification_service.notify_admins_new_support_ticket()`.

Администраторам отправляется inline-клавиатура с переходом к карточке тикета в админке.

---

## 6. Отмена обращения

`cancel_support()` обрабатывает callback `support:cancel`.

Он:

- подтверждает callback;
- очищает FSM;
- сообщает, что обращение отменено;
- возвращает пользователя в главное меню.

Отмена до отправки текста не создаёт запись в БД.

---

## 7. Helpers

`helpers_support.py` содержит:

- `build_support_request_text()` — prompt для пользователя;
- `build_support_already_open_text(ticket_id)` — сообщение, если тикет уже открыт;
- `build_support_already_open_after_create_text(ticket_id)` — защита от гонки при создании;
- `build_support_cancel_keyboard()` — inline-кнопка отмены;
- `format_datetime()` — формат дат для текстов.

---

## 8. Связь с админкой

Пользовательский support flow только создаёт тикет. Дальше тикет живёт в admin-разделе:

- `handlers/admin/support.py` показывает список открытых тикетов;
- администратор пишет ответ;
- ответ доставляется через `NotificationService`;
- `SupportService.mark_admin_replied()` фиксирует ответ;
- закрытие выполняется через `SupportService.close_ticket_by_admin()`.

---

## 9. Правила разработки

1. Не создавать второй открытый тикет для того же пользователя.
2. При тикете из заявки всегда проверять доступ пользователя к заявке.
3. Не хранить текст обращения в FSM после создания тикета.
4. Уведомления администраторам отправлять через `NotificationService`.
5. Если добавляется вложение/фото в поддержку, нужно расширять schema/service/model, а не только handler.