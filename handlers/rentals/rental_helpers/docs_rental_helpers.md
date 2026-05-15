# Важно

> **[Recoverable ошибка]()** → 
>   - показываем сообщение
>   - не чистим FSM (пользователь может попробовать снова)
>
> **[Fatal ошибка]()** → 
>   - завершаем rent-flow через единый helper: 
>     - обновить rent-UI, если он уже есть
>     - иначе ответить обычным сообщением + state.clear()
>
> **[Recoverable]()**:
>   - ServiceError при чтении деталей
>
> **[Fatal]()**:
>  - битый `callback` → показываем ошибку + кнопка назад
>  - сделка/item не найдена/нет доступа/сломанные данные → показываем “не найдено” + кнопка назад

---

# RentalKeyboardHelpers

[**UI-helper для клавиатур FSM-сценария аренды**]()

### Методы:

> `build_start_date_keyboard` - **[Собирает клавиатуру выбора даты начала аренды]()**
>  * Принимает: `item_id` / `days_ahead`
  * Внутри:
    - берёт текущую UTC-дату
    - строит кнопки дат на несколько дней вперёд
    - добавляет служебную кнопку-заголовок
    - добавляет кнопку возврата к объявлению
  * `Callback` каждой даты:
    - `START_DATE_CB + дата ("%d.%m.%Y")`

> `build_rent_cancel_keyboard` - **[Собирает клавиатуру после отмены аренды]()**
>  * Принимает: `item_id`
   * Добавляет кнопки:
     - `🔙 Назад к объявлению` (если `item_id` есть)
     - `🏠 Главное меню`


> `build_rent_success_keyboard` - **[Собирает клавиатуру после успешной отправки запроса аренды]()**
  * Добавляет кнопки:
    - `📋 Мои сделки`
    - `🏠 Главное меню`

### Что использует:
- `datetime` / `timezone` / `timedelta`
- `ITEM_DETAILS` / `START_DATE_CB` / `BACK_TO_MENU_CB` / `MY_RENTALS_CB` / `IGNORE_CB` / `START_DATE_DAYS_AHEAD`

---

# RentalLoadHelpers

[**FSM-helper для загрузки сущностей и восстановления rental draft context**]()

### Методы:

> `load_item` - **[Загружает сущность по id через переданный loader]()**
> * Принимает: `loader` / `entity_id` / `invalid_id_text` / `load_error_text` / `not_found_text` / `rent_ui_message_id`
> 
> Норм?:
> * Типизация: loader - `Callable[[int], Awaitable[T | None]]`
> * Возвращает: `-> T | None`

> Если `entity_id is None`:
>    - считает это `fatal`-ошибкой: **[некорректная кнопка | нет `item_id` → чистим FSM и выходим]()**
>    - вызывает `abort_rent_flow(...)`
>    - возвращает `None`
> 
> Если `loader` выбросил `ServiceError`:
>    - считает это `recoverable`-ошибкой: **[сервис/БД временно недоступны, FSM не трогаем (→ остаёмся в этом шаге)]()**
>    - показывает `load_error_text`
>    - не чистит FSM
>    - возвращает `None` (или `show_my_rentals`?)
> 
> Если сущность не найдена:
>    - считает это `fatal`-ошибкой: **[объявления нет → чистим FSM]()**
>    - вызывает `abort_rent_flow(...)`
>    - возвращает `None` (или `show_my_rentals`?)
> 
> Если сущность найдена:
>    - возвращает её


> `get_rent_end_date_context_or_abort` - **[Восстанавливает context для шага выбора даты окончания]()**
>
> Читает из FSM:
>    - `rent_ui_message_id`
>    - `rent_draft`
> 
> Валидирует `rent_draft` через `RentalCreateDraft`
> 
> Если `draft` повреждён:
>    - считает это `fatal`-ошибкой: **[draft повреждён → завершаем flow]()**
>    - вызывает `abort_rent_flow(...)`
>    - возвращает `None`
> 
> Если нет `start_date`:
>    - считает это `fatal`-ошибкой: **[нет `start_date` → завершаем flow]()**
>    - вызывает `abort_rent_flow(...)`
>    - возвращает `None`
> 
> Если всё корректно возвращает:
>    - `draft`
>    - `rent_ui_message_id`
>    - `start_date_str`

Тут важно: добавил аргумент `data_err`
(`data_err` = "❌ Данные аренды повреждены. Начните заново." = `rental_data_err`)


> `get_rent_confirm_context_or_abort` - **[Восстанавливает context для финального подтверждения аренды]()**
>
> Читает из FSM:
>    - `rent_ui_message_id`
>    - `rent_draft`
> 
> Валидирует `rent_draft` через `RentalCreateDraft`
> 
> Если draft повреждён:
>    - считает это `fatal`-ошибкой: **[draft повреждён → завершаем flow]()**
>    - вызывает `abort_rent_flow(...)`
>    - возвращает `None`
> 
> Проверяет наличие обязательных данных:
>    - `item_id`
>    - `owner_id`
>    - `renter_id`
>    - `start_date`
>    - `end_date`
> 
> Если данных не хватает:
>   - считает это `fatal`-ошибкой: **[не хватает данных → завершаем flow]()**
>   - вызывает `abort_rent_flow(...)`
>   - возвращает `None`
> 
> Если всё корректно возвращает:
>    - `draft`
>    - `rent_ui_message_id`

### Что использует:
- `send_or_edit` / `abort_rent_flow`
- `ServiceError` / `ValidationError`
- `RentalCreateDraft`

---

# RentalStoreHelpers

[**FSM-helper для записи данных аренды в `RentalCreateDraft`**]()

### Методы:

> `store_rent_start_date_or_abort` - **[Записывает дату начала аренды в draft и обновляет FSM]()**
> * Принимает: `callback` / `state` / `start_str` / `rent_data_err` / `invalid_id_text`
>
> Читает из FSM:
>    - `rent_ui_message_id`
>    - `rent_draft`
>
> Валидирует `rent_draft` через `RentalCreateDraft`
>
> Если `draft` повреждён:
>    - считает это `fatal`-ошибкой: **[draft повреждён → завершаем flow]()**
>    - вызывает `abort_rent_flow(...)`
>    - возвращает `None`
>
> Если нет `item_id`:
>    - считает это `fatal`-ошибкой: **[некорректная кнопка | нет `item_id` → чистим FSM и выходим]()**
>    - вызывает `abort_rent_flow(...)`
>    - возвращает `None`
>
> Если всё корректно:
>    - записывает `draft.start_date = start_str`
>       - В draft храним строку. Переведем в `datetime` внутри confirm-функции
>    - обновляет FSM через `state.update_data(...)`
>    - возвращает:
>      - `draft.item_id`
>      - `rent_ui_message_id`


> `store_rent_end_date_and_amounts` - **[Записывает дату окончания и рассчитанные суммы аренды в draft]()**
> * Принимает: `state` / `draft` / `end_str` / `item` / `total_price`
>
> Внутри записывает 
>   - `draft.end_date`
>   - `draft.total_price`
>   - `draft.deposit_amount`
>       - `deposit_amount` уже может быть проставлен на старте из `item.deposit`
> 
> Обновляет FSM через `state.update_data(...)`
>
> Если всё корректно возвращает: `None`

### Что использует:
- `abort_rent_flow`
- `ValidationError`
- `RentalCreateDraft`

---

# RentalTextsHelpers

[**Text-helper для сообщений FSM-сценария аренды**]()

### Важно
- `item.deposit` возможно лучше форматировать через `format_price(...)` (см. `utils.functions`)
- сами составления ответов возможно нужно еще пересмотреть для точности.


### Константы:

Текст ошибки:
* `not_item_id` - если не удалось распознать id объявления
* `not_item_for_rental` - если не удалось определить объявление для аренды
* `not_item` - если объявление не найдено
* `serv_item_err` - если сервис не смог загрузить объявление
* `date_err_msg` - некорректной даты начала аренды
* `rental_data_err` - повреждённых данных аренды
* `not_all_rental_data_err` - неполных данных для создания аренды
* `no_rent_data_err` - невозможности восстановить данные аренды
* `cancel_rent` - отмены аренды

### Методы:

> `format_item_not_available_message` - **[Формирует UX-текст, если вещь уже недоступна для аренды]()**
> 
> Принимает: `exc: ItemNotAvailable`
>
> Внутри берёт из `ItemNotAvailable`: `end_date` / `status` / `rental_id`
> 
> Если `end_date`
> - есть: показывает, до какой даты вещь занята
> - нет: показывает общий текст занятости


> `format_start_date_rent_text` - **[Формирует текст первого экрана аренды]()**

> `format_end_date_rent_text` - **[Формирует текст шага-выбора даты окончания аренды]()**

> `format_rent_confirmation_text` - **[Формирует текст экрана подтверждения аренды]()**
> * Принимает: `item` / `start_date_str` / `end_date_str` / `days` / `price_per_day` / `total_price` / `deposit` / `total_with_deposit`

> `build_success_text` - **[Формирует текст успешной отправки запроса аренды]()**
> * Принимает: `item` / `start_date` / `end_date` / `days` / `total_price` / `deposit`

### Что использует:
- `Decimal`
- `ItemNotAvailable`

---

# RentalValidateHelpers

[**UX-validation helper для callback parsing, дат, периода аренды, доступности вещи и расчёта стоимости**]()

### Методы:

> `parse_rent_item_id` - **[Парсит `item_id` из callback data начала аренды]()** - по сути это `parse_callback`, но без `prefix`
>
> Принимает: `data`
>
> * Если `data` пустая: возвращает `None`
> * Если `data` повреждена: возвращает `None`
> * Если `item_id` распознан: возвращает `int`


> `parse_and_valid_start_date_str` - **[Парсит и валидирует дату начала аренды из callback data]()**
> 
>    - `start_str` - dd.mm.YYYY (12.03.2025)
>    - `start_date` - date (2025, 3, 12)
>
> Если callback data повреждена:
>    - считает это `fatal`-ошибкой: **[битый callback-data → завершаем flow]()**
>
> Если дата начала невалидна:
>    - FSM не чистит
>    - возвращает `None`
>
> Если всё корректно возвращает:
>    - `start_str`
>    - `start_date`


> `parse_and_validate_end_date` - **[Парсит дату окончания и длительность аренды из callback data]()**
>
> Парсит: 
>   - `end_str` - "15.03.2025"
>   - `days` - 3
>   - `end_date`
>
> Если `callback data` повреждена:
>    - считает это `fatal`-ошибкой: **[некорректная дата окончания → завершаем flow]()**
>
> Если `days < 1`:
>    - считает это `fatal`-ошибкой: **[некорректная длительность (кнопка битая) → завершаем flow]()**
>
> Если всё корректно возвращает: `end_str` / `end_date` / `days`


> `parse_rental_id` - **[Парсит `rental_id` из callback действия сделки]()**
>
> Ожидает формат: `["rental_action", "confirm", "<id>"]` - `rental_action:<action>:<rental_id>`
>
> Если `callback data` 
> - корректная: возвращает `rental_id`
> - повреждена: возвращает `None`


> `get_rental_id_or_alert` - **[Получает `rental_id` из callback или показывает alert]()**
>
> Если `rental_id` не распарсился:
>    - `Fatal`[-ошибка](): некорректная кнопка → нельзя звать сервис/перерисовывать UI
>    - показывает alert: `Некорректная кнопка.`
>    - возвращает `None`
>
> Если `rental_id` распознан: возвращает `rental_id`
>
> * Это UX-guard для повреждённых / старых / подменённых callback-кнопок
> * После `None` handler должен сразу сделать `return`


> `ensure_rent_item_available_or_notify` - **[Проверяет доступность вещи перед продолжением rent-flow]()**
> 
> Принимает: `callback` / `rental_service` / `item_id`
>
> Внутри вызывает `rental_service.ensure_item_available(item_id)`
>
> Если вещь недоступна
>    - ловит `ItemNotAvailable`: `Recoverable`-ошибка: **[вещь занята, просто показываем сообщение]()**
>    - возвращает `True` - вещь недоступна
>
> Если вещь доступна: возвращает `False`
>
> Доменная проверка делегирована в `RentalService` (ДО запуска выбора дат): защита от 
>   - старых кнопок
>   - старых сообщений
>   - гонок
>   - параллельных кликов


> `reject_own_item_rent` - **[Показывает ранний UX-guard, если пользователь пытается арендовать свою вещь]()**
> * Принимает: `item` / `user_id`
>
> Если `item.user_id == user_id`:
>    - считает это `recoverable`-ошибкой: **[пользователь просто ошибся, FSM не чистим]()**
>    - FSM не чистит
>    - возвращает `True`
>
> Если вещь не принадлежит пользователю: возвращает `False`
>
> Важно:
>    - это бизнес-правило должно быть продублировано/закреплено в service-layer
>    - в helper это допустимо только как ранний UX-guard


> `validate_rent_start_date` - **[Проверяет, что дата начала аренды не сегодня и не в прошлом]()**
>
> Принимает: `start_date`
> * Если дата сегодня или раньше: возвращает текст ошибки
> * Если дата корректна: возвращает `None`
>
> Использует `datetime.now(timezone.utc).date()`


> `validate_rent_dates` - **[Конвертирует строки дат из draft в aware UTC datetime]()**
> * Принимает: `start_date_str` / `end_date_str` / `rent_ui_message_id`
>
> Если даты повреждены:
>    - считает это `fatal`-ошибкой: **[даты битые → завершаем flow]()**
>
> Если дата окончания не позже даты начала:
>    - считает это `recoverable`-ошибкой: **[логическая ошибка → остаёмся в confirmation]()**
>
> Если всё корректно:
>    - создаёт `aware datetime` в UTC
>    - считает количество дней
>
> Если всё корректно возвращает: `start_dt` / `end_dt` / `days_count`
>
> Норм?:
> * Должно использовать `timezone.utc`, а не локальную timezone

> Было (локальную timezone):
>    - `tz = datetime.now(timezone.utc).astimezone().tzinfo`
>    - `start_dt = datetime.combine(start_date, time.min).replace(tzinfo=tz)`
>    - `end_dt = datetime.combine(end_date, time.min).replace(tzinfo=tz)`
> 
> Сейчас:
>    - `start_dt = datetime.combine(start_date, time.min, tzinfo=timezone.utc)`
>    - `end_dt = datetime.combine(end_date, time.min, tzinfo=timezone.utc)`


> `validate_rent_period_or_notify` - **[Проверяет период аренды по ограничениям вещи и показывает UX-ошибки]()**
> * Принимает: `start_date_str` / `end_date` / `days` / `item` / `rent_ui_message_id`
>
> Проверяет:
>    - корректность даты начала
>    - что дата окончания позже даты начала
>    - фактическое число дней
>    - минимальный срок аренды
>    - максимальный срок аренды
>
> Если дата начала повреждена:
>    - считает это `fatal`-ошибкой: **[некорректная дата начала]()**
>
> Если период не проходит ограничения:
>    - считает это `recoverable`-ошибкой: 
>      - **[пользователь выбрал “не туда” → остаёмся в шаге `end_date` (без clear)]()**
>      - **[не фейлим, а синхронизируем на фактическое значение]()**
>      - **[коротко → остаёмся на выборе end_date]()**
>      - **[длинно → остаёмся на выборе end_date]()**
>
> Если всё корректно:
>    - возвращает актуальное количество дней


> `calculate_total_rent_price` - **[Считает цену за день и итоговую стоимость аренды]()**
> * Принимает: `price_per_day` / `days`
>
> Внутри:
>    - приводит цену к `Decimal`
>    - считает `total_rent_price = normalized_price * days`
>    - округляет итог до `0.01`
>
> Если всё корректно возвращает:
>    - `normalized_price`
>    - `total_rent_price`
> 
> `price` может быть `Decimal` — ок. Если вдруг `float/int` — приведём к `Decimal`.


### Что использует:
- `datetime` / `timezone` / `time` / `date`
- `Decimal`
- `RentalService`
- `send_or_edit` / `abort_rent_flow`
- `ItemNotAvailable`
- `format_item_not_available_message` / `date_err_msg`

---

# RentalNotificationHelpers

[**Helper для best-effort уведомления владельца о новом запросе аренды**]()

Возможно сыровата.

### Методы:

> `notify_item_owner_about_rent_request` - **[Отправляет владельцу уведомление о новом запросе аренды]()**
> * Принимает: `notification_service` / `owner_tg_id` / `item` / `renter` / `rental_id`
>
> Если `owner_tg_id is None`:
>    - уведомление не отправляется
>    - функция просто завершает выполнение
>    - основной `rent-flow` не ломается
>
> Если `owner_tg_id` есть:
>    - отправляет уведомление через `notification_service.notify_user(...)`
>
> "Не удалось отправить уведомление владельцу user_id=%s: отсутствует telegram_id или владелец не найден"

### Что использует:
- `NotificationService`
- `ItemOut` / `UserOut`
- `get_open_rental_keyboard`
- `format_new_rental_request`


