# Item

---

## 1. SHOW

[**Для показа объявлений и их деталей**]()

> `show_my_items_entry`: `"📦 Мои объявления"` : `MY_ITEMS_PREFIX` - [Показывает список объявлений пользователя]()
>
> Вызывает `show_my_items(...)`

> `show_item_details`: `SHOW_ITEM_CB` - [Показывает детали объявления]()
> 
>- подтверждает callback: `callback.answer()`
>- получает объявление через `load_item(...)`
>- сохраняет выбранное объявление в FSM через `store_selected_item(...)`
>- загружает контекст объявления через `load_item_category_context(...)`
>- строит клавиатуру через `build_my_item_details_keyboard(...)`
>- показывает список подкатегории/объявлений через `send_or_edit(...)`
> 
> В конце `data` содержит:
>   - `id` (`item`)
>   - `name` (`-`)

---

## 2. FLOW CREATE

[**FSM-router для сценария создания объявления**]()

> Начинает процесс создания объявления (оба сценария: с категорией и без неё)
>
> * [**_Сценарий 1_**]() (главное меню «📦 Сдать в аренду»): `event = Message`
>   - категории ещё нет → сразу просим название и ставим FSM на `title`
>   - категория / подкатегория пока неизвестны → просто создаём болванку и просим название:
>     - `category_id = 999`
>     - `subcategory_id = 999`
>
> * [**_Сценарий 2_**]() (после выбора подкатегории): `event = CallbackQuery` с `data` вида `"subcat:<id>"`
>   - извлекаем `subcategory_id`, берём category по `parent_id`, сохраняем в FSM и просим название.
>   - «➕ Добавить объявление» (inline-кнопка внутри списка «Мои объявления»)

###  СЦЕНАРИЙ 2 (`Callback`) 

> `start_create_item_from_my_items`: `ADD_ITEM_CB` - [Запуск процесса создания объявления из списка `Мои объявления`]()
>
* Подтверждает callback: `callback.answer()`
* Очистим все предыдущие данные `await state.clear()`
   - `data` сейчас пусто
* `draft = ItemCreateDraft()` 
   - `category_id/title/price` ещё `None`
   - дефолтные поля будут заполнены БД
* Инициализация FSM - данные которые можно заполнить сразу
   - `new_item=draft.model_dump()` - пока пусто, начнем заполнять
* Переводим FSM в первое состояние - _**[выбор категории]()**_
* Показывает экран выбора категории
 
В конце `data` содержит:
   - `mode`
   - `new_item`
   - `user` (`id`)

> `show_subcategories_for_creating_item`: `CAT_FI_PREFIX` - [Показывает подкатегории для выбранной категории]()
  * Получает категорию / подкатегории
  * Сохраняет выбранную категорию в FSM
  * FSM пока остаётся в состоянии `category`
      - переход произойдёт позже — при выборе конкретной подкатегории
  * Показывает экран выбора подкатегорий

В конце `data` содержит:
   - `mode`
   - `new_item`
   - `id` (`user | category`)
   - `name` (`category`)

> `start_create_item_from_subcategory`: `SUBCAT_FI_PREFIX` - [Переходит из выбранной подкатегории к вводу названия вещи]()
  * Получает подкатегорию / категорию
  * Валидируем черновик `ItemCreateDraft` из FSM (FSM все_равно хранит `dict`)
  * Записывает: `category_id` / `subcategory_id`
  * Сохраняет выбор в FSM
  * Передаёт управление в общий (для двух сценариев) шаг `start_create_item_title(...)`

В конце `data` содержит:
   - `mode`
   - `new_item`
   - `id` (`user | category | subcat`)
   - `name` (`category | subcat`)

###  СЦЕНАРИЙ 1 (`Message`)

> `start_create_item_from_menu` - [Запускает создание объявления из меню без заранее выбранной категории]()
  * Очищает FSM
  * Инициализирует `draft`
  * Сейчас использует временные заглушки:
    - `category_id = 999`
    - `subcategory_id = 999`
  * Передаёт управление в общий (для двух сценариев) шаг `start_create_item_title(...)`

В конце `data` содержит:
   - `mode`
   - `new_item`
   - `id` (`user | category | subcat`)
   - `name` (`category | subcat`)

### Начинается FSM для обоих сценариев

> `start_create_item_title` - [Показывает пользователю первый шаг ввода названия вещи]()
>  * Переводит FSM в состояние ожидания названия `ItemCreateStates.title`
>  * Отправляет текст шага через `send_or_edit(...)` 
>    - `get_back_inline_keyboard()`
>
>`f"[FSM] → Старт создания объявления ({'из меню.' if category is None else 'из подкатегории.'})"`

> `process_item_title` - [Обрабатывает ввод названия вещи]()
> - `get_back_inline_keyboard()`
> - `get_back_inline_keyboard("back_to_item_title")`
>
> `process_item_description` - [Обрабатывает ввод описания]()
> - `get_back_inline_keyboard("back_to_item_title")`
> - `get_back_inline_keyboard("back_to_item_description")`
>
> `process_item_price` - [Обрабатывает ввод цены аренды]()
> - `get_back_inline_keyboard("back_to_item_description")`
> - `get_back_inline_keyboard("back_to_item_price")`
> 
> `process_item_deposit` - [Обрабатывает ввод залога]()
> - `get_back_inline_keyboard("back_to_item_price")`
> - `get_back_inline_keyboard("back_to_item_deposit")`
> 
> `process_item_location` - [Обрабатывает ввод местоположения]()
> - `get_back_inline_keyboard("back_to_item_deposit")`
> - `get_back_inline_keyboard("back_to_item_location")`
>
> `process_item_rental_period` - [Обрабатывает ввод минимального срока аренды]()
> - `get_back_inline_keyboard("back_to_item_location")`
> - ``

>* Для каждого шага `handler`:
>  - читает ввод пользователя
>  - валидирует через helper
>  - обновляет `ItemCreateDraft` в FSM
>  - переводит FSM в следующее состояние
>  - показывает следующий UX-шаг

### ЛОГИКА ДОБАВЛЕНИЯ ФОТОГРАФИЙ

> `photos_done` - [Завершает шаг загрузки фотографий]()
>  * `photo` держим отдельно от `ItemCreateDraft`
>  * Читает список фото из FSM
>  * Переводит FSM в `confirmation`
>  * Показывает итоговое подтверждение
>
> `process_item_photos` - [Добавляет фото в список FSM]()
>  * Берёт `file_id` фото лучшего качества
>  * Проверяет лимит `MAX_PHOTOS`
>  * Сохраняет список `photos` в FSM
>
> `photos_wrong_input` - [Обрабатывает неверный ввод на шаге фото]()
>  * Просит пользователя отправить фото или нажать “✅ Готово”
> 
> `get_photos_keyboard()` - ✅ Готово / 🔙 Назад   (`reply keyboard`)

### ФИНАЛЬНЫЕ ОБРАБОТКИ

> `show_item_confirmation` - [Показывает итоговое подтверждение объявления]()
>  * Валидирует `draft` из FSM
>  * Извлекает контекст подтверждения
>  * Показывает preview
>
> `process_item_confirmation`: `PUBLISH_ITEM_CB` - [Обработка подтверждения ✅ публикации объявления]()
>  * Читает `new_item` из FSM
>  * Валидирует: `ItemCreateDraft` и `ItemCreate`
>  * Создаёт объявление через `item_service.create(...)` (дефолты устанавливает Модель/БД!)
>  * Если есть фото: прикрепляет их отдельно через `photo_service`
>  * Показывает сообщение об успешном создании
>  * Очищает FSM
>  * Возвращает пользователя в главное меню
>
> `cancel_flow_to_main_menu`: `CANCEL_ITEM_CB` - [Полностью отменяет создание объявления]()
>  * `F.data == CANCEL_ITEM_CB`?
>  * Подтверждает `callback`
>  * Очищает FSM
>  * Убирает reply-клавиатуру
>  * Возвращает пользователя в главное меню
>
> `start_process_edit_item`: `EDIT_ITEM_CB` - [Начинает сценарий редактирования объявления]()
>  * Загружает `item`
>  * Инициализирует `edit-context` в FSM
>  * Показывает стартовый экран редактирования
> 
> (логика не завершена)

### Что использует:
- `Message`
- `CallbackQuery`
- `FSMContext`
- `ItemService`
- `PhotoService`
- `CategoryService`
- `ItemCreateDraft`
- `ItemCreate`
- `ItemCreateStates`
- `send_or_edit`
- `ServiceError`
- `ValidationError`
- `parse_callback`
- `create_helpers as ch`
- `show_main_menu`

### Возвращает:
- `None`

### return
- `await send_or_edit(...)`
- `await message.answer(...)`
- `await show_main_menu(...)`
- `await show_item_confirmation(...)`


---

- `await state.clear()` - Полностью очищаем FSM (состояние + данные)
- `await state.set_state(None)` - 🔄 Очищает состояние, но сохраняет данные. FSM “выйдет” из состояния, но `state_data` (например, `new_item`) сохранится.
- `await state.update_data(new_item={})` - сбросить только объявление. ✏️ Изменяет / очищает часть данных.