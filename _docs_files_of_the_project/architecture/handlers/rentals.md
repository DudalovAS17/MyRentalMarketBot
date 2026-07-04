# Rentals — создание, просмотр и клиентские действия по заявкам аренды

Раздел описывает пользовательские handlers аренды. В текущем проекте аренда — это заявка клиента на товар компании. Клиент создаёт заявку, администратор обрабатывает её в админке, а клиент может смотреть детали и отменять заявку до подтверждения.

---

## 1. Карта файлов

| Файл                                 | Назначение                                                                               |
|--------------------------------------|------------------------------------------------------------------------------------------|
| `handlers/rentals/router.py`         | Общий `rental_router`.                                                                   |
| `handlers/rentals/flow_create.py`    | FSM создания заявки на аренду.                                                           |
| `handlers/rentals/details.py`        | Список «Мои заявки» и карточка заявки.                                                   |
| `handlers/rentals/actions.py`        | Клиентские действия над заявкой, сейчас — отмена.                                        |
| `handlers/rentals/rental_helpers/*`  | Клавиатуры, тексты, загрузка, валидация, UI и хранение draft.                            |
| `handlers/rentals/create_helpers.py` | Re-export helpers для create flow.                                                       |
| `handlers/rentals/trash.py`          | Старый/пустой файл, не часть актуального flow.                                           |
| `handlers/otzivi.py`                 | Черновой/старый flow отзывов, сейчас не должен считаться завершённой актуальной логикой. |

---

## 2. Подключение

`rental_router` подключается в `app/routers.py` одним из первых, до `base_router`. Это важно, потому что аренда использует FSM-сообщения и callback-и, которые не должны попадать в базовый текстовый catch-all.

---

## 3. `flow create`: Создание заявки, общий сценарий

FSM использует `RentalCreateStates`:

1. `period` — выбор фиксированного периода;
2. `comment` — ввод количества дней, даты и комментария одним сообщением;
3. `confirmation` — подтверждение создания заявки.

Во временном FSM-контексте хранятся:

- `rent_draft` — сериализованный `RentalCreateDraft`;
- `rent_ui_message_id` — ID сообщения-экрана аренды, которое перерисовывается по шагам.

---

### `start_rent_process()`

Стартует по callback `RENT_ITEM_CB + item_id` из карточки товара.

Алгоритм:

1. подтверждает callback;
2. парсит `item_id`;
3. загружает товар через `item_service.get_item_by_id`;
4. проверяет доступность товара через `rental_service.get_open_rental_for_item` в helper-е `abort_if_item_unavailable()`;
5. создаёт `RentalCreateDraft` с `item_id`, `client_name`, `client_phone`;
6. очищает старый FSM;
7. сохраняет draft и ID UI-сообщения;
8. показывает клавиатуру выбора периода;
9. ставит `RentalCreateStates.period`.

Источник `user_id` для будущей заявки не берётся из FSM: при подтверждении используется актуальный `user.id` из middleware.

---

### `process_fixed_period()` - Выбор периода

Обрабатывает callback `RENT_PERIOD_CB` только в состоянии `RentalCreateStates.period`.

Действия:

- парсит код периода;
- достаёт draft из FSM;
- повторно загружает товар;
- повторно проверяет доступность;
- рассчитывает итоговую цену через helper `calculate_price_for_fixed_period_total()`;
- сохраняет `rental_period_text` и `total_price` в draft;
- перерисовывает UI и просит пользователя отправить детали;
- переводит FSM в `RentalCreateStates.comment`.

---

### `process_rent_details_message()` - Детали заявки

Принимает сообщение клиента в формате:

```text
3 - 25.06.2026 - Нужна доставка вечером
```

Парсер `parse_rent_details_message()` возвращает:

- количество дней;
- дату, к которой нужен товар;
- необязательный комментарий.

После успешного парсинга обработчик:

1. достаёт draft;
2. загружает товар;
3. проверяет доступность;
4. сохраняет `client_comment`;
5. строит текст подтверждения;
6. показывает клавиатуру подтверждения;
7. ставит `RentalCreateStates.confirmation`.

Количество дней и дата сейчас используются в тексте подтверждения; бизнес-цена считается по выбранному фиксированному периоду.

---

### `confirm_rent()` - Подтверждение

Callback `CONFIRM_RENT_CB` в состоянии `confirmation`.

Алгоритм:

1. достаёт draft;
2. повторно загружает товар;
3. повторно проверяет доступность;
4. собирает `RentalCreate`;
5. вызывает `rental_service.create(payload)`;
6. загружает детали заявки;
7. уведомляет клиента через `notification_service.notify_user_rental_created()`;
8. уведомляет администраторов через `notification_service.notify_admins_new_rental()`;
9. показывает экран успеха;
10. очищает FSM.

Если создание заявки не удалось, пользователю показывается безопасная ошибка, FSM не должен создавать частичные записи вручную.

---

### `cancel_rent_flow()` - Отмена create flow

`cancel_rent_flow()` срабатывает по `CANCEL_RENT_FLOW_CB`.

Он:

- читает `rent_ui_message_id` и `item_id` из draft;
- перерисовывает UI текстом отмены;
- очищает FSM.

Это отмена черновика, а не отмена уже созданной заявки в БД.

---

## 4. `details`: Просмотр заявок 

### `view_my_rentals()`

Срабатывает на:

- текст `📋 Мои сделки`;
- callback `MY_RENTALS_CB`.

Фактически показывает пользовательские заявки через entry-функцию `show_my_rentals()`.

### `show_rental_details()` и `render_rental_details()`

Карточка заявки открывается по `RENTAL_DETAILS_CB + rental_id`.

`render_rental_details()`:

- вызывает `rental_service.get_rental_details(rental_id, current_user_id=user.id)`;
- не показывает чужие заявки;
- строит UI через `build_rental_details_ui(details)`;
- отправляет/редактирует сообщение.

---

## 5. `actions`: Клиентская отмена заявки

`rental_cancel_by_client()` обрабатывает callback `CLIENT_CANCEL_RENTAL_CB + rental_id`.

Логика:

1. парсит и проверяет ID заявки;
2. вызывает `rental_service.cancel_by_client(rental_id=rental_id, user_id=user.id)`;
3. при успехе уведомляет клиента и администраторов;
4. перерисовывает карточку заявки.

Отмена доступна только если сервис разрешает переход статуса. После подтверждения администратором кнопка отмены клиенту не должна показываться.

---

## 6. Правила разработки

1. Перед каждым критичным шагом аренды повторно загружать товар и проверять доступность.
2. `user_id` всегда брать из middleware, а не из callback/FSM.
3. FSM хранит только draft и UI-контекст, не является источником истины.
4. Все изменения статусов заявки выполнять через `RentalService`/`AdminRentalService`.
5. Уведомления отправлять через `NotificationService`, а не напрямую из бизнес-логики репозитория.