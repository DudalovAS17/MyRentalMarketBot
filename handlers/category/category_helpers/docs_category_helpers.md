# CategoryKeyboardHelpers

[**UI-helper для клавиатур category-flow**]()

### Методы:

> `build_subcategories_keyboard` - **[Собирает клавиатуру подкатегорий выбранной категории]()**
> * Принимает: 
>   - `subcategories` `: list[CategoryOut]`?
>   - `category` `: CategoryOut`?
>
> Внутри:
>    - строит кнопки подкатегорий
>    - prefix `SUBCAT_CB_PREFIX`
>    - добавляет кнопку: `📋 Все в категории {category.name}`
>    - добавляет кнопку: `🔙 Назад (к категориям)`


> `build_back_to_item_details_keyboard` - **[Собирает клавиатуру возврата к деталям объявления]()**
> * Принимает: `item_id`
>
> Внутри:
>    - создаёт одну inline-кнопку: `🔙 Назад (к деталям объявления)`
>    - callback ведёт обратно на экран деталей объявления


### Что использует:
- `build_category_keyboard`
- `SUBCAT_CB_PREFIX` / `ALL_CATEGORY_CB` / `BACK_TO_CAT` / `ITEM_DETAILS_CB`

---

# CategoryLoadHelpers

[**Load-helper для загрузки сущностей в category-flow**]()

> Норм?:
> * Типизация: `loader: Callable[[int], Awaitable[T | None]]`
> * Возвращает: `T | None`

### Методы:

> `resolve_entity` - **[Загружает сущность или показывает UX-ошибку при невозможности продолжить flow]()**

> `load_entity_or_notify` - **[Загружает данные через loader или уведомляет пользователя об ошибке]()**

> Они оба похожи друг на друга:
> 
> Принимает: `loader` / `entity_id`
>
> Если `entity_id is None`:
>    - показывает `invalid_id_text`
>    - возвращает `None`
>
> Если `loader` выбросил `ServiceError`:
>    - показывает `load_error_text`
>    - возвращает `None`
>
> Если сущность не найдена:
>    - показывает `not_found_text` через 
>      - `callback.answer(..., show_alert=True)` - **[resolve_entity]()**
>      - `send_or_edit(...)` - **[load_entity_or_notify]()**
>    - возвращает `None` (или `await show_categories(callback, category_service)`)
>
> Если сущность найдена:
>    - возвращает её

### Что использует:
- `Callable` / `Awaitable` / `TypeVar`
- `send_or_edit`
- `ServiceError`

---

# CategoryStoreHelpers

[**FSM-helper для сохранения выбранного контекста category-flow**]()

Стоит так сделать?
- `category: CategoryOut`
- `subcategory: CategoryOut`

### Методы:

> `store_selected_category` - **[Сохраняет выбранную категорию в FSM и сбрасывает вложенный контекст]()**
> * Принимает: `category`
> * Записывает в FSM `id` и `name` категории

> `store_selected_subcategory` - **[Сохраняет выбранную подкатегорию в FSM и сбрасывает выбранное объявление]()**
> * Принимает: `subcategory`
> * Записывает в FSM `id` и `name` подкатегории

> `store_selected_item` - **[Сохраняет выбранное объявление в FSM]()**
> * Принимает: `item_id`
> * Записывает в FSM: `id` объявления

---

# CategoryTextsHelpers

[**Text-helper для сообщений category-flow и карточки объявления**]()

! Нужно переделать логику `item.is_available` !

### Константы:

Текст ошибки, если
- `not_cat_id` - **[не удалось распознать категорию]()**
- `serv_err_cat` - **[категорию не удалось загрузить через сервис]()**
- `not_cat` - **[категория не найдена]()**
- `not_subcat_id` - **[не удалось распознать подкатегорию]()**
- `serv_err_subcat` - **[подкатегорию не удалось загрузить через сервис]()**
- `not_subcat` - **[подкатегория не найдена]()**
- `not_item_id` - **[не удалось распознать объявление]()**
- `not_item` - **[объявление не найдено]()**
- `serv_err_item` - **[объявление не удалось загрузить через сервис]()**
- `serv_err_items` - **[список объявлений не удалось загрузить через сервис]()**
- `serv_err_photo` - **[фото не удалось загрузить через сервис]()**
- `not_photos` - **[фото для объявления не найдены]()**

### Методы:

> `item_details_text` - **[Формирует текст карточки объявления для category-flow]()**
> * Принимает: `item` / `category_name` / `subcategory_name`

### Что использует:
- `ItemOut`
- `format_price`
- `format_days`

---

# CategoryFormattersHelpers

[**Small helper для форматирования занятости и media group в category-flow**]()

> Типизация должна быть такая?:
>   - `open_rental: RentalOut | None`
>   - `photos: Sequence[PhotoOut]`

### Методы:

> `busy_until_text` - **[Возвращает дату окончания открытой аренды в формате `dd.mm.YYYY`]()**
> * Принимает: `open_rental`


> `build_photo_media` - **[Собирает media group для отправки фотографий объявления]()**
> * Принимает: `photos`
>
> Внутри:
>    - проходит по списку фото
>    - берёт `photo.telegram_file_id`
>    - создаёт `InputMediaPhoto(...)`
>
> Если всё корректно возвращает:
>    - `list[InputMediaPhoto]`

### Что использует:
- `InputMediaPhoto`
- `Sequence`
- `PhotoOut`
- `RentalOut`