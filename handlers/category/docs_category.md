# Category

[**Router-файл для сценария просмотра категорий, подкатегорий и объявлений в ветке «Арендовать»**]()

### Основа:

- подтверждает callback: `callback.answer()`
- получает категорию/подкатегорию/объявление через `resolve_entity(...)`
- сохраняет выбранную категорию/подкатегорию/объявление в FSM через `store_selected_(...)`
- загружает подкатегории/объявления через `load_entity_or_notify(...)`
- строит клавиатуру через `build_(...)`
- показывает список подкатегории/объявлений через `send_or_edit(...)`

### Методы:

> `back_to_categories`: `BACK_TO_CAT` - [Возвращает пользователя к списку категорий]()
>
> Вызывает `show_categories(...)`

> `show_subcategories`: `CAT_CB_PREFIX` - [Показывает список подкатегорий выбранной категории]()
> 
> `ОСНОВА`
> 
> В конце `data` содержит:
>   - `id` (`category`)
>   - `name` (`category`)

> `show_items_in_subcategory`: `SUBCAT_CB_PREFIX` - [Показывает список объявлений выбранной подкатегории]()
>
> `ОСНОВА`
> 
> В конце `data` содержит:
>   - `id` (`category | subcategory`)
>   - `name` (`category | subcategory`)
>
>Можно добавить `limit: int = 10`: ограничение по количеству объявлений

> `show_item_details_in_subcategory`: `ITEM_DETAILS_CB` - [Показывает детальную информацию по объявлению]()
>
> `ОСНОВА` +
>* читает из FSM: `selected_category_name`/`selected_subcategory_name`/`selected_subcategory_id`
>* проверяет занятость через `rental_service.get_open_rental_for_item(...)`
> 
> В конце `data` содержит:
>   - `id` (`category | subcategory | item`)
>   - `name` (`category | subcategory`)
>
> Логику "отправляем главное фото" - возможно реализуем позже

> `show_all_photos`: `SHOW_ALL_PHOTOS_CB` - [Показывает все фотографии объявления альбомом]()
>
> Логика: "если уже показывали" — пока оставим это
>
>* парсит `item_id` из callback
>* загружает фото через `load_entity_or_notify(...)`
>* пытается удалить прошлое сообщение (это не обязательно - но удобно)
>* формирует media через `build_photo_media(...)`
>* отправляет альбом через `answer_media_group(...)`
>* затем отправляет отдельное сообщение с кнопкой “назад” через `send_reply(...)`
> 
> В конце `data` содержит:
>   - `id` (`category | subcategory | item`)
>   - `name` (`category | subcategory`)

Эта часть кода возможно не идеальна:
```python
try:
    open_rental = await rental_service.get_open_rental_for_item(item.id)
except ServiceError:
    open_rental = None  # если проверка не удалась — не блокируем UX
```

---

### Constants

- `BACK_TO_CAT`
- `CAT_CB_PREFIX`
- `SUBCAT_CB_PREFIX`
- `ITEM_DETAILS_CB`
- `SHOW_ALL_PHOTOS_CB`

### Что использует:
- `Router`
- `TelegramBadRequest`
- `show_categories`
- `resolve_entity`
- `load_entity_or_notify`
- `store_selected_category`
- `store_selected_subcategory`
- `store_selected_item`
- `item_details_text`
- `build_subcategories_keyboard`
- `build_items_keyboard`
- `build_item_details_kb`
- `build_back_to_item_details_keyboard`
- `busy_until_text`
- `build_photo_media`
- `send_or_edit`
- `send_reply`
- `ServiceError`
- `parse_callback`

### return
- `await show_categories(...)`
- `await send_or_edit(...)`
- `await send_reply(...)`
- `await callback.message.answer_media_group(...)`