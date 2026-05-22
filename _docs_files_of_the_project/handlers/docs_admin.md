# AdminItemsHandlers

[**Router-файл для админ-модерации объявлений**]()

> Важно:
>    - callback data хранит строку: `PENDING` / `ACTIVE` / `HIDDEN`
>    - service получает enum: `ItemStatus.PENDING` / `ItemStatus.ACTIVE` / `ItemStatus.HIDDEN`

### Методы:

### Menu / list

> `admin_items_list` - **[Показывает меню модерации объявлений]()**
> * показывает стартовый экран раздела - `get_admin_items_menu_keyboard()`

> `admin_items_filter` - **[Показывает первую страницу объявлений выбранного статуса]()**

> `admin_items_page` - **[Показывает страницу списка объявлений]()**

> `admin_items_view` - **[Показывает карточку объявления]()**
> * `get_admin_item_details_keyboard(...)`

### Status actions

> `admin_items_approve` - **[Переводит объявление в ACTIVE]()**

### Отклонение объявления

> `admin_items_reject_ask` - **[Запрашивает причину отклонения объявления]()**
> * Внутри:
>    - переводит FSM в `AdminStates.waiting_item_reject_reason`
>    - просит админа ввести причину

> `admin_items_reject_apply` - **[Применяет отклонение объявления с причиной]()**

### Скрыть объявление / Вернуть объявление

> `admin_items_hide` - **[Скрывает активное объявление]()**

> `admin_items_unhide` - **[Возвращает скрытое объявление в ACTIVE]()**


# AdminUsersHandlers

[**Router-файл для админ-управления пользователями**]()

Файл отвечает за admin-flow управления пользователями: просмотр меню, поиск пользователя по `user_id`, 
просмотр карточки, бан и разбан пользователя.  

>* Найти по `user_id` - `admin:users:find`
>* 🚫 Ban - `admin:users:ban:{user_id}`
>* ✅ Unban - `admin:users:unban:{user_id}`
>* 🔄 Обновить - `admin:users:view:{user_id}`

### Методы:

### Menu / view

> `admin_users_menu` - **[Показывает меню управления пользователями]()**
> * очищает FSM
> * показывает экран: `👥 Управление пользователями`

> `admin_users_view` - **[Показывает карточку пользователя по callback-кнопке]()**

### Search by user_id

> `admin_users_find` - **[Запрашивает user_id для поиска пользователя]()**
> * переводит FSM в состояние:  `AdminStates.waiting_user_id`
> * просит админа ввести `user_id`
>
> `admin_users_find_message` - **[Обрабатывает введённый user_id и показывает карточку пользователя]()**
>
> Внутри:
>    - если `user_id` не распарсился:
>      - показывает сообщение: `Введите корректный user_id (число):`
>      - FSM не очищает
>      - пользователь остаётся в этом же шаге
>    - если `user_id` корректный:
>      - очищает FSM через `state.clear()`
>      - показывает карточку через `show_user_card(...)`

### Ban flow

> `admin_users_ban_prompt` - **[Запрашивает причину бана пользователя]()**
>
> Внутри:
>- если `user_id is None`:
>  - завершает handler
>- если `user_id` корректный:
>  - переводит FSM в состояние: `AdminStates.waiting_user_ban_reason`
>  - сохраняет в FSM: `target_user_id`
>  - просит админа ввести причину бана
>
> `admin_users_ban_apply` - **[Применяет бан пользователя с причиной]()**
>
> Внутри:
>- читает FSM data через `state.get_data()`
>- достаёт: `target_user_id`
>- достаёт и очищает текст причины из `message.text`
>- если причины нет: `Укажите причину бана текстом.`
>  - FSM не очищает
>  - пользователь остаётся в этом же шаге
>- если данные корректны:
>  - очищает FSM через `state.clear()`
>  - вызывает `apply_user_action_and_show_card(...)`


### Unban flow

> `admin_users_unban` - **[Разбанивает пользователя]()**
>
> Внутри:
>- если `user_id is None`:
>  - завершает handler
>- если `user_id` корректный:
>  - вызывает `apply_user_action_and_show_card(...)`


# AdminDealsHandlers

[**Router-файл для админ-управления сделками аренды**]()

>Админ должен уметь:
>    - увидеть последние сделки (пагинация)
>    - открыть конкретную сделку (по кнопке из списка и по ID)
>    - увидеть детали (участники, предмет, даты, статус)
>    - выполнить админ-действия (минимум: cancel + resolve dispute), строго по whitelist
>
> callbacks:
>* `admin:deals` — вход в раздел | 🔙 К списку
>* `admin:deals:page:<n>` — пагинация (⬅️ Пред | ➡️ След)
>* `admin:deals:view:<rental_id>` — 🔎 Открыть карточку сделки | 🔄 Обновить
>* `admin:deals:by_id` — 🔎 Открыть по ID
>* `admin:deals:action:<rental_id>:<action>` — действие админа
>* `admin:menu` — 🔙 Назад в админ-меню
>* `admin:deals:resolve:{rental_id}` - ✅ Закрыть спор
>* `admin:deals:cancel:{rental_id}` - 🚫 Отменить сделку
>
> Что тут есть:
>- ✅ Раздел “Сделки” в админке
>- ✅ Список последних сделок (пагинация)
>- ✅ Открытие сделки по кнопке
>- ✅ Открытие сделки по ID (FSM)
>- ✅ Отмена сделки с причиной (FSM) + лог в admin_actions
>- ✅ Закрытие спора (только если DISPUTED) + лог в admin_actions
>- ✅ Безопасная модель действий (whitelist условий)
>
>**[Экран 1: “Последние сделки”]()**
> - Список 5–10 штук:
>    - #ID | статус | предмет | даты
> - Кнопки:
>    - Открыть #123
>    - ➡️ След / ⬅️ Пред (если надо)
>    - 🔎 Открыть по ID
>    - 🔙 Назад в админ-меню
>
>**[Экран 2: “Карточка сделки”]()**
> - Текст:
>   - Rental ID
>   - статус
>   - item (название)
>   - owner / renter (id, username)
>   - start/end
>   - created_at
> - Кнопки:
>   - 🚫 Отменить (просит причину)
>   - ✅ Закрыть спор (если в dispute)
>   - 🔄 Обновить
>   - 🔙 Назад к списку
>
> **_Whitelist переходов_** (админские действия должны быть “безопасными”, чтобы не сломать логику аренды):
> - cancel - разрешено (если статус не COMPLETED/CANCELLED)
> - resolve_dispute - только если статус DISPUTE
>
> **_Audit Log - каждое админ-действие логируем:_**
>    - `admin_id`
>    - `action_type` (CANCEL_RENTAL, RESOLVE_DISPUTE)
>    - `entity` (rental, rental_id)
>    - `payload` (reason/resolution)
>    - `created_at`


### Методы:

### List / pagination

> `admin_deals_list` - **[Показывает первую страницу списка последних сделок]()**

> `admin_deals_page` - **[Показывает страницу списка сделок]()**

### Deal details

> `admin_deals_view` - **[Показывает карточку конкретной сделки]()**

### Open by ID

> `admin_deals_open_by_id` - **[Запрашивает ID сделки у админа]()**
> - переводит FSM в `AdminStates.waiting_rental_id` (FSM хранит только временное ожидание ввода)
> - просит ввести ID сделки

> `admin_deals_process_id` - **[Обрабатывает введённый ID сделки и показывает карточку]()**
>
> Внутри:
>    - парсит текст
>    - если ID некорректный:
>      - просит ввести число
>      - FSM не очищает
>    - если ID корректный:
>      - очищает FSM
>      - загружает details через service
>      - показывает карточку сделки

### Cancel flow

> `admin_deals_cancel_ask` - **[Запрашивает причину отмены сделки]()**
> - переводит FSM в `AdminStates.waiting_cancel_reason`
> - просит ввести причину отмены

> `admin_deals_cancel_apply` - **[Применяет отмену сделки с причиной]()**
> 
> Внутри:
>    - получает `rental_id` из FSM
>    - если `rental_id` отсутствует:
>      - очищает FSM
>      - показывает UX-ошибку
>      - завершает handler
>    - проверяет текст причины
>    - если причина пустая:
>      - просит ввести причину снова
>      - FSM не очищает
>    - если причина есть:
>      - очищает FSM
>      - вызывает `admin_rental_service.admin_cancel_rental(...)`
>      - передаёт `admin_tg_id=message.from_user.id`
>      - если service вернул `False`:
>        - показывает UX-ошибку
>      - если успешно:
>        - загружает details
>        - показывает обновлённую карточку сделки


### Resolve dispute flow

> `admin_deals_resolve_ask` - **[Запрашивает текст решения по спору]()**

> `admin_deals_resolve_collect_resolution` - **[Сохраняет текст решения по спору и запрашивает итоговый статус]()**
>
> Внутри:
>    - получает `rental_id` из FSM
>    - если `rental_id` отсутствует:
>      - очищает FSM
>      - показывает UX-ошибку
>      - завершает handler
>    - проверяет текст решения
>    - если решение пустое:
>      - просит ввести текст снова
>      - FSM не очищает
>    - если решение есть:
>      - переводит FSM в `AdminStates.waiting_dispute_target`
>      - сохраняет `resolution`
>      - показывает keyboard выбора исхода через `get_admin_dispute_target_keyboard(...)`


> `admin_deals_resolve_apply_target` - **[Закрывает спор с выбранным итоговым статусом]()**
> 
> Внутри:
>    - получает `resolution` из FSM
>    - парсит target status через `parse_dispute_target(...)`
>    - вызывает `admin_rental_service.admin_resolve_dispute(...)`
>    - передаёт:
>      - `rental_id`
>      - `admin_tg_id=callback.from_user.id`
>      - `resolution`
>      - `target_status`
>    - очищает FSM после service-call
>    - если service вернул `False`:
>      - показывает alert
>    - если успешно:
>      - загружает details
>      - показывает обновлённую карточку сделки




# AdminSupportHandlers

[**Router-файл для админ-управления тикетами поддержки**]()

>✅ Definition of Done (проверка за 2 минуты)
> - Пользователь пишет /support → бот просит текст → создаётся тикет → “принято”
> - Всем админам прилетает сообщение с кнопками “Открыть/Ответить/Закрыть”
> - Админ: “Открыть” → видит карточку
> - Админ: “Ответить” → пишет → пользователю приходит сообщение
> - Админ: “Закрыть” → пользователю приходит уведомление + тикет исчезает из open-списка

### Методы:

### List / pagination

> `admin_support_list` - **[Показывает первую страницу открытых тикетов поддержки]()**

> `admin_support_list_page` - **[Показывает страницу списка открытых тикетов]()**

### Ticket details

> `admin_support_view` - **[Показывает карточку тикета поддержки]()**

### Reply flow

> `admin_support_reply_prompt` - **[Запрашивает текст ответа на тикет]()**
> - переводит FSM в `AdminSupportStates.waiting_reply_text`
> - сохраняет `ticket_id`
> - просит админа ввести ответ

> `admin_support_reply_send` - **[Отправляет ответ пользователю и пишет audit log]()**
>
> - загружает открытый тикет
> - отправляет ответ пользователю
> - пишет audit log 
> - очищает FSM
> - показывает success-сообщение

### Close flow

> `admin_support_close` - **[Закрывает открытый тикет поддержки]()**
> * Принимает: `callback` / `support_service` / `admin_service` / `user`
>
> Внутри:
> - загружает открытый тикет
> - уведомляет пользователя о закрытии тикета
> - пишет audit log
> - загружает обновлённый ticket
> - перерисовывает карточку тикета


### Что использует:
- `AdminStates`
- `get_admin_users_menu_keyboard`
- `send_or_edit`
- `show_user_card`
- `get_admin_user_id_or_alert`
- `parse_admin_user_id`
- `apply_user_action_and_show_card`
- `parse_admin_item_status`
- `AdminRentalService`
- `show_deals_list`
- `format_deal_details`
- `parse_admin_page`
- `parse_admin_rental_id`
- `parse_admin_rental_id_text`
- `parse_dispute_target`
- `parse_resolve_target_callback`
- `get_admin_deal_details_keyboard`
- `get_admin_dispute_target_keyboard`
- `SupportService`
- `AdminActionService`
- `AdminSupportStates`
- `SupportTicketStatus`
- `format_ticket_card`
- `show_support_ticket_list`
- `is_open_ticket`
- `show_support_ticket_card_or_not_found`
- `parse_support_page`
- `parse_support_ticket_id`
- `get_admin_support_ticket_keyboard`
- `send_or_edit`
