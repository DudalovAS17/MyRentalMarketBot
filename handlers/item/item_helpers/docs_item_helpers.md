# ItemCommonHelpers

НЕРАЗОБРАНО!

---

# ItemKeyboardHelpers

[**UI-helper для клавиатур item-flow**]()

### Методы:

> `build_back_to_my_items_keyboard` - **[Собирает клавиатуру возврата к списку моих объявлений]()**
> * Принимает: —
> * `🔙 Назад (к моим объявлениям)` - `MY_ITEMS_PREFIX`

> `build_create_item_categories_keyboard` - **[Собирает клавиатуру выбора категории при создании объявления]()**
> * Принимает: `categories`
> * `🔙 Назад в меню` - `BACK_TO_MENU_CB`

> `build_create_item_subcategories_keyboard` - **[Собирает клавиатуру выбора подкатегории при создании объявления]()**
> * Принимает: `subcategories`
> * `🔙 Назад (к категориям)` - `BACK_TO_CAT`

> `build_item_confirmation_keyboard` - **[Собирает клавиатуру подтверждения создания объявления]()**
> * Принимает: —
> * `✅ Разместить объявление` - `PUBLISH_ITEM_CB`
> * `❌ Отмена` - `CANCEL_ITEM_CB` (`BACK_TO_MENU_CB`)

### Что использует:
- `build_category_keyboard`
- `MY_ITEMS_PREFIX` / `CAT_FI_PREFIX` / `SUBCAT_FI_PREFIX`
- `PUBLISH_ITEM_CB` / `CANCEL_ITEM_CB`
- `BACK_TO_MENU_CB` / `BACK_TO_CAT`

---

# ItemLoadHelpers

[**Load/UI-helper для item**]()

### Методы:

> `load_item` - **[Загружает item или показывает UX-ошибку]()**

> `load_entity_or_notify` - **[Загружает сущность через loader или показывает UX-ошибку]()**

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
>    - возвращает `None` (или `show_my_items()`)
>
> Если сущность не найдена:
>    - показывает `not_found_text` через
>      - `send_or_edit(...)` + добавляет `markup_back` - **[load_item]()**
>      - `send_or_edit(...)` - **[load_entity_or_notify]()**
>    - возвращает `None` (или `show_my_items()`)
>
> Если сущность найдена:
>    - возвращает её


> `load_item_category_context` - **[Получает названия категории и подкатегории для карточки item]()**
> 
> Принимает: `category_service` / `item`
>
> Внутри:
>- возвращает имена категории и подкатегории
>- если `CategoryService` выбросил `ServiceError`:
>  - возвращает `("-", "-")`
>  - не ломает item details UI


> `show_create_item_categories_step` - **[Показывает шаг выбора категории при создании объявления]()**
> * Принимает: `callback` (или  `event: CallbackQuery | Message`) / `category_service`
>
> Внутри:
>- загружает корневые категории
>- обновляет экран через `send_or_edit(...)`
>- если `CategoryService` выбросил `ServiceError`:
>  - показывает короткий UX-ответ
>  - завершает выполнение


> `send_item_confirmation_preview` - **[Отправляет preview объявления с фото или текстовым fallback]()**
> * Принимает: `message` / `text` / `photos` / `keyboard`
>
> Если `photos` есть: _пытается отправить первое фото с caption_
>
> Если отправка фото не удалась из-за `TelegramBadRequest`: _отправляет обычное текстовое сообщение_
>
> Если `photos` нет: _отправляет обычное текстовое сообщение_
>
> `TelegramBadRequest` норм?


> `attach_item_photos_or_warn` - **[Прикрепляет фото к созданному объявлению или предупреждает пользователя]()**
> * Принимает: `callback` / `photo_service` / `item_id` / `photos`
>
> Внутри:
>- если валидных фото нет: просто завершает выполнение
>- если валидные фото есть: вызывает `photo_service.create_photos(...)`
>- если `PhotoService` выбросил `ServiceError`:
>  - просто показывает предупреждение пользователю и идём дальше
>  - не ломает уже созданное объявление

### Что использует:
- `TelegramBadRequest`
- `Callable` / `Awaitable` / `TypeVar`
- `CategoryService` / `PhotoService`
- `CategoryOut` / `ItemOut`
- `build_create_item_categories_keyboard`
- `create_item_category_step_text`
- `send_or_edit`
- `ServiceError`

---

# ItemStoreHelpers

[**FSM-helper для сохранения контекста item-flow**]()

### Методы:

> `store_selected_item` - **[Сохраняет выбранное объявление в FSM]()**
> * Принимает: `item_id`
> * Записывает в FSM `id` объявления

> `store_selected_category` - **[Сохраняет выбранную категорию и сбрасывает вложенный FSM-контекст]()**
> * Принимает: `category`
> * Записывает в FSM `id` и `name` категории

> `store_selected_subcategory` - **[Сохраняет выбранную подкатегорию и draft создания объявления]()**
> * Принимает: `state` / `category` / `subcategory` / `draft`
> * Записывает в FSM:
>    - `id` и `name` категории
>    - `id` и `name` подкатегории
>    - `new_item` - сохраняется через `draft.model_dump(mode="json")`


> `init_edit_item_context` - **[Инициализирует FSM-контекст редактирования объявления]()**
> * Принимает: `state` / `item`
> * Записывает в FSM:
>    - `edit_item_id`
>    - `edit_field = None`

### Что использует:
- `ItemCreateDraft`

---

# ItemTextsHelpers

[**Text-helper для экранов item-flow: список, детали, создание и редактирование объявления**]()

### Константы:

Текст ошибки, если
- `not_cat_id` - **[не удалось распознать категорию]()**
- `serv_err_cat` - **[категории не удалось загрузить через сервис]()**
- `not_cat` - **[категория не найдена]()**
- `not_subcat_id` - **[не удалось распознать подкатегорию]()**
- `serv_err_subcat` - **[подкатегорию не удалось загрузить через сервис]()**
- `not_subcat` - **[подкатегория не найдена]()**
- `not_item_id` - **[не удалось распознать объявление]()**
- `not_item` - **[объявление не найдено]()**
- `serv_err_item` - **[объявление не удалось загрузить через сервис]()**
- `photo_or_ready` - **[на шаге фото пользователь отправил не фото]()**
- `data_item_not_found` - **[draft объявления не найден в FSM]()**
- `cant_create_item_err` - **[объявление не удалось создать]()**
- `draft_item_valid_err` - **[draft объявления повреждён]()**
- `create_item_valid_err` - **[create DTO объявления не проходит валидацию]()**


`no_photos` - **[Текст предупреждения, если пользователь не загрузил фотографии]()**


### Методы:

> `my_items_screen_text` - **[Формирует текст экрана списка моих объявлений]()**
> * Принимает: `count = len(items)`

> `item_details_text` - **[Формирует текст карточки объявления]()**
> * Принимает: `item` / `category_name` / `subcategory_name`
> * Убери логику `item.is_available`!

> `create_item_category_step_text` - **[Формирует текст шага выбора категории]()**
> * Принимает: —

> `create_item_subcategory_step_text` - **[Формирует текст шага выбора подкатегории]()**
> * Принимает: `category_name`

> `create_new_item_text` - **[Формирует текст начала создания объявления]()**
> * Принимает: `category` / `subcategory`

> `build_item_description_step_text` - **[Формирует текст шага ввода описания]()**
> * Принимает: —

> `build_item_price_step_text` - **[Формирует текст шага ввода цены аренды]()**
> * Принимает: —

> `build_item_deposit_step_text` - **[Формирует текст шага ввода залога]()**
> * Принимает: —

> `build_item_location_step_text` - **[Формирует текст шага ввода местоположения]()**
> * Принимает: —

> `build_item_min_period_step_text` - **[Формирует текст шага ввода минимального срока аренды]()**
> * Принимает: —

> `build_item_photo_step_text` - **[Формирует текст шага загрузки фотографий]()**
> * Принимает: —

> `build_item_photo_max_photos_warning` - **[Формирует предупреждение о лимите фотографий]()**
> * Принимает: —

> `build_item_photo_success_or_more` - **[Формирует текст успешной загрузки фото]()**
> * Принимает: `len_photos`

> `build_item_confirmation_text` - **[Формирует preview объявления перед публикацией]()**
> * Принимает: `draft` / `category_name` / `subcategory_name` / `photos_count`

> `build_item_created_success_text` - **[Формирует текст успешного создания объявления]()**
> * Принимает: `title`

> `edit_item_start_text` - **[Формирует стартовый текст редактирования объявления]()**
> * Принимает: `item`

### Что использует:
- `ItemCreateDraft` / `ItemOut`
- `get_items_count_str`
- `format_money_value` / `format_deposit_value` / `format_photos_count`
- `short_description`
- `format_days` / `format_price`
- `MAX_PHOTOS`

---

# ItemValidateHelpers

[**Validation-helper для пользовательского ввода и preview context в item create-flow**]()

Стоит ли добавлять `.strip()` во всех функциях?
Например: `title = title.strip()`

### Методы:

> `validate_item_title` - **[Проверяет название объявления]()**
> * Принимает: `title`
> * `3 < title < 255`
> * Если название корректное: возвращает `None`

> `validate_item_description` - **[Проверяет описание объявления]()**
> * Принимает: `description`
> * `description` > 10
> * Если описание корректное: возвращает `None`

> `validate_item_price` - **[Проверяет цену аренды и приводит её к `Decimal`]()**
> * Принимает: `price_text`
> * Приводит к `Decimal`
> * `price_text` > 0
> * Если цена корректная: возвращает `None` и `price`

> `validate_item_deposit` - **[Проверяет сумму залога и приводит её к `Decimal`]()**
> * Принимает: `deposit_text`
> * Приводит к `Decimal`
> * `price_text` >= 0
> * Если цена корректная: возвращает `None` и `deposit`

> `validate_item_min_period` - **[Проверяет минимальный срок аренды и приводит его к `int`]()**
> * Принимает: `rental_period`
> * Приводит к `int`
> * `price_text` > 1
> * Если цена корректная: возвращает `None` и `min_days`

> `short_description` - **[Возвращает короткую версию описания для preview]()**
> * Принимает: `description` / `limit`

> `extract_item_confirmation_context` - **[Извлекает category/subcategory/photos context для preview объявления]()**
> * Принимает: `data`
>
> Если category/subcategory нет:
>    - использует fallback:
>      - `будет уточнена модератором`
>
> Если photos нет:
>    - возвращает пустой список
>
> Если всё корректно возвращает:
>    - `category_name`
>    - `subcategory_name`
>    - `photos`


### Что использует:
- `InvalidOperation`