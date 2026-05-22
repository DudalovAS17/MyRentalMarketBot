## File Items 

> `_show_items_list` - **[Показывает список объявлений по статусу для админ-модерации]()**
> * Принимает: `status` / `page`
>
> Внутри:
>    - получает объявления
>    - передаёт в сервис
>    - сохраняет в FSM:
>      - `admin_items_page`
>      - `admin_items_status = status.value`
>    - формирует текст списка
>
> Если объявлений нет:
>    - показывает empty-state
>    - строит пустую list-keyboard

> `_format_item_details` - **[Формирует текст карточки объявления для админки]()**

> `_get_admin_item_id_or_alert` - **[Получает item_id из callback data или показывает alert]()**
> * Принимает: `callback`
>
> Если `item_id` распарсился:
>    - возвращает `item_id`
>
> Если callback data повреждена:
>    - показывает alert:
>      - `Некорректный ID`
>    - возвращает `None`

> `_apply_item_status_action` - **[Применяет admin status-action к объявлению и перерисовывает карточку]()**
> * Принимает: `event` / `item_service` / `item_id` / `new_status` / `reason`
>
> Внутри:
>    - вызывает `item_service.admin_set_status(...)`
>    - передаёт `new_status: ItemStatus`
>    - передаёт `reason`, если он есть
>    - если service вернул `None` / `False`: завершает выполнение
>    - если статус изменён: формирует карточку