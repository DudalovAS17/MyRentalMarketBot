# Rental 

---

# RentalDetails

[**Router-файл для открытия списка сделок и просмотра деталей конкретной сделки**]()

### Методы:

> `view_my_rentals` - [Router-wrapper для экрана “Мои сделки”]()
>  * Срабатывает на:
>    - reply-кнопку `📋 Мои сделки`
>    - callback `MY_RENTALS_CB`
>    - `"back_to_rentals"`
>  * Внутри:
>    - делегирует работу в `show_my_rentals(...)`

> `show_rental_details` - [Обрабатывает callback открытия деталей сделки]()
>  - подтверждает `callback` через `callback.answer()`
>  - парсит `rental_id` из `callback data`
>  - передаёт управление в `render_rental_details(...)`

### Helper

> `render_rental_details` - [Рендерит экран деталей сделки]()
> - получает детали сделки
> - если сервисная ошибка - `Recoverable`: временная ошибка сервиса/БД - завершает выполнение
> - если деталей нет - `Recoverable`: нет доступа/не найдено - завершает выполнение

### Что использует:
- `build_rental_details_ui`
- `send_or_edit`

---

# RentalFlowCreate

[**FSM-router для создания запроса аренды вещи**]()


### Методы:

> `start_rent_process`: `RENT_ITEM_CB` - **[Запускает rent-flow после нажатия кнопки аренды]()**
>
> Убрал 
>   - `@rental_router.callback_query(F.data.startswith("back_to_start_date:"))`
>   - `logger.info(f"Пользователь {user.id} начинает процесс аренды для товара {item.id}")`
> 
> Внутри:
>    - парсит `item_id` из `callback data` через `parse_rent_item_id(callback.data)`
>      - возможно лучше через `parse_callback(callback.data, RENT_ITEM_CB)`
>    - получаем товар `item` через `load_item_or_abort(...)`
>    - проверки:
>      - [пользователь не арендует свою вещь?]() - через `reject_own_item_rent(...)`
>      - [вещь доступна?]() - через `ensure_rent_item_available_or_notify(...)`
>    - создаёт `RentalCreateDraft`: `item_id` / `renter_id` / `owner_id` / `deposit_amount`
>    - очищает FSM перед новым rent-flow
>    - сохраняет в FSM:
>      - `rent_draft`
>      - `rent_ui_message_id`
>    - ✅ отправляем ОТДЕЛЬНОЕ сообщение - “экран аренды” (не трогаем карточку объявления), чтобы дальше редактировать только его
>    - переводит FSM в `RentalCreateStates.start_date`
>
> `return`, если:
> - `item` не найден 
> - `callback` повреждён
> - если вещь недоступна


> `process_start_date`: `START_DATE_CB` - **[Обрабатывает выбор даты начала аренды]()**
>
> Внутри:
>    - парсит и валидирует [дату начала]() через `parse_and_valid_start_date_str(...)`
>    - записывает `start_date` в `RentalCreateDraft`
>    - загружает `item` и проверяет доступность вещи
>    - рендерит экран выбора [даты окончания]() через `render_rent_ui(...)`!
>    - переводит FSM в `RentalCreateStates.end_date`
>
> `return`, если 
>   - дата повреждена
>   - не загрузился item


> `process_end_date`:`END_DATE_CB` - **[Обрабатывает выбор даты окончания и показывает подтверждение аренды]()**
>
> Внутри:
>    - парсит `end_date` и `days`
>    - восстанавливает `RentalCreateDraft` из FSM
>    - загружает `item` и проверяет доступность вещи
>    - валидирует период аренды `days`
>    - считает `price_per_day` и `total_price`
>    - записывает [дату окончания]() и [сумму]() в `draft`
>    - строит клавиатуру подтверждения
>    - считает `total_with_deposit`
>    - рендерит confirmation экран через `render_rent_ui(...)`
>    - переводит FSM в `RentalCreateStates.confirmation`


> `confirm_rent`: `CONFIRM_RENT_CB` - **[Создаёт запрос аренды со статусом REQUESTED и показывает экран успеха]()**
>
> **_Логика уведомлений возможно сыровата!_**
> 
> Убрал: `logger.info(f"[Rent] Создана аренда #{new_rental.id}")`
> 
> Внутри:
>    - восстанавливает финальный rental context из FSM
>    - загружает `item` и проверяет доступность вещи
>    - конвертирует [строки дат]() в `aware UTC datetime` через `validate_rent_dates(...)`
>    - собирает `RentalCreate`
>      - `renter_id=user.id` - берём из контекста (middleware), не доверяем state на 100%
>      - `owner_id=item.user_id` - берём из контекста (item), не доверяем state на 100% - не `draft.owner_id`
>    - создаёт аренду
>    - best-effort получает `owner_tg_id`
>    - отправляет уведомление владельцу через `notify_item_owner_about_rent_request(...)`
>    - рендерит success экран через `render_rent_ui(...)`
>    - очищает FSM 
>
> Если `RentalCreate` не проходит валидацию:
>    - считает это `fatal`[-ошибкой](): данные не проходят строгую схему → завершаем flow
>
> Если `rental_service.create(...)` выбросил `ServiceError`:
>    - считает это `recoverable`[-ошибкой](): сервис не создал (например, конфликт/БД) → остаёмся в confirmation
>    - FSM не чистит
>    - пользователь остаётся на confirmation step


> `cancel_rent_flow`:`CANCEL_RENT_FLOW_CB` - **[Отменяет rent-flow и возвращает пользователя к безопасному экрану]()**
>
>- подтверждает `callback`
>- читает из FSM: `rent_ui_message_id` / `rent_draft` / `item_id`
>- рендерит экран отмены через `render_rent_ui(...)`
>- очищает FSM


> `ignore_callback`: `IGNORE_CB` - **[No-op обработчик для служебных кнопок-заголовков]()**
>
> Просто вызывает `callback.answer()`

### Что использует:
- `RentalCreateStates`
- `RentalCreate` / `RentalCreateDraft`
- `ServiceError` / `ValidationError`
- `send_or_edit` / `render_rent_ui` / `abort_rent_flow`
- `build_rent_end_date_keyboard` / `build_rent_confirmation_keyboard`
- `RENT_ITEM_CB` / `START_DATE_CB` / `END_DATE_CB` / `CONFIRM_RENT_CB` / `CANCEL_RENT_FLOW_CB` / `IGNORE_CB`
- `create_helpers as ch`

---

# RentalActions - САМА СДЕЛКА МЕЖДУ ВЛАДЕЛЬЦЕМ И АРЕНДАТОРОМ

[**Router-файл для callback-действий над сделкой аренды**]()


`service_call=lambda: rental_service.(...)`?

### Методы:

#### Основной метод

> `_run_rental_action` - **[Единая обвязка для atomic action над сделкой]()**
>
> - вызывает переданный service-method `service_call()`
> - обрабатывает исключения (`ServiceError`)
> - показывает UX-ответ через  `callback.answer(...)`
> - перерисовывает детали сделки через `render_rental_details(...)` (всегда после `fail/ok`, кроме crash)
>
> Типы ситуаций:        
> 1) Если service-method выбросил `ServiceError`:
>    - считает это `recoverable infra`[-ошибкой](): **[БД/тайм-аут/сервис недоступен (НЕ бизнес-логика)]()**
>    - показывает `alert`: `Ошибка. Попробуйте позже.`
>    - не перерисовывает детали сделки
>    - завершает выполнение `return`. Почему `return` сразу (тут НЕ должно быть `render_rental_details`): 
>      - мы не знаем, изменился ли статус
>      - UI может стать ложным
>      - нельзя продолжать
>
> 2) Если service-method вернул `False` (`ok = False`):
>    - считает это `recoverable business`-отказом: **[Бизнес-отказ]()**
>       - **[статус уже не `REQUESTED`]()**
>       - **[пользователь не владелец]()**
>       - **[другой пользователь успел раньше]()**
>    - показывает `alert`: `fail_text`
>      - Почему здесь `show_alert=True`: пользователь ожидал действие → нужно явно объяснить, почему “не сработало”
>      - даже при `fail` — перерисуем, чтобы UI был актуальным и пользователь должен увидеть новый статус/новые кнопки
>    - перерисовывает детали сделки
>    - завершает выполнение
>
> Если service-method вернул `True`:
>    - показывает `ok_text`
>    - перерисовывает детали сделки

> - `service_call: Callable[[], Awaitable[bool]]`
> - пример: `rental_service.confirm_requested(rental_id=rental_id, actor_id=user.id)`
> - `ok_text` - пример: "Подтверждено" из await callback.answer()
> - `fail_text` - пример: "Не удалось подтвердить (статус уже изменился или нет прав)."

> - ✅ корректно обрабатывает все 3(2?) типа ошибок
> - ✅ не смешивает бизнес и инфраструктуру
> - ✅ всегда приводит UI в актуальное состояние


### Request actions

> `rental_confirm` - **[Подтверждает запрос аренды владельцем]()**
> * Service-call: `.confirm_requested(...)`

> `rental_reject_by_owner` - **[Отклоняет запрос аренды владельцем]()**
> * Service-call: `.reject_requested_by_owner(...)`

> `rental_reject_by_renter` - **[Отменяет запрос аренды арендатором]()**
> * Service-call: `.reject_requested_by_renter(...)`


### Confirmed cancellation actions

> `rental_cancel_confirmed_by_owner` - **[Отменяет подтверждённую аренду владельцем]()**
> * Service-call: `.cancel_confirmed_by_owner(...)`

> `rental_cancel_confirmed_by_renter` - **[Отменяет подтверждённую аренду арендатором]()**
> * Service-call: `.cancel_confirmed_by_renter(...)`


### Active cancellation actions

> `rental_cancel_active_by_owner` - **[Отменяет активную аренду владельцем]()**
> * Service-call: `.cancel_active_by_owner(...)`

> `rental_cancel_active_by_renter` - **[Отменяет активную аренду арендатором]()**
> * Service-call: `.cancel_active_by_renter(...)`


### Handover / receive flow (это не статусы, а булевый флаг)

> Чтобы `ACTIVE` означал реальный факт передачи, нам нужна “двухсторонняя фиксация”:
> - владелец нажал «Передал вещь»
> - арендатор нажал «Получил вещь»
> - только когда оба события произошли → переводим в ACTIVE
>
> В `ACTIVE` меняется всё:
> - появляются основания для спора,
> - отмена превращается в “разрыв активной аренды” (другие последствия),
> - начинается (или считается) срок,
> - можно “завершить” только после факта возврата.
>
> Архитектурно правильно: не плодить статусы (типа `“owner_handed_over”`), а хранить “подтверждения-флаги” 
> отдельными полями в самой сделке.
>
> И `status` желательно передавать как `Enum`, не как строку (чтобы UI работал типобезопасно):
> - `status: rental.status` (`Enum`)
> - `status_value: rental.status.value` (если нужно для текста)

> `rental_handover_owner` - **[Фиксирует передачу вещи владельцем]()**
> * Service-call: `.confirm_handover_by_owner(...)`

> `rental_receive_renter` - **[Фиксирует получение вещи арендатором]()**
> * Service-call: `.confirm_receive_by_renter(...)`

> По аналогии нужно будет добавить флаг ОПЛАТЫ
>   - добавляешь в модель Rental: `payment_confirmed_at: datetime | None` (или payment_status)
>   - (позже) Оплата/холд: ✅/⏳
>   - добавляешь кнопку/процесс оплаты в CONFIRMED
>   - в activate_if_ready добавляешь условие: payment_confirmed_at IS NOT NULL


### Finish / dispute actions

> `rental_complete` - **[Завершает активную аренду владельцем]()**
> * Service-call: `.complete_active(...)`

> `rental_dispute` - **[Открывает спор по сделке]()**
> * Service-call: `.open_dispute(...)`

### Что использует:
- `rental_router`
- `RentalService`
- `ServiceError`
- `render_rental_details`

---



