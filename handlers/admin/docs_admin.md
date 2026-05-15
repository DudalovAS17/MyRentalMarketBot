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


### Что использует:
- `AdminStates`
- `parse_admin_item_status`


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


### Что использует:
- `AdminStates`
- `get_admin_users_menu_keyboard`
- `send_or_edit`
- `show_user_card`
- `get_admin_user_id_or_alert`
- `parse_admin_user_id`
- `apply_user_action_and_show_card`
