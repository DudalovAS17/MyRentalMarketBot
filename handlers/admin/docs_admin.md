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