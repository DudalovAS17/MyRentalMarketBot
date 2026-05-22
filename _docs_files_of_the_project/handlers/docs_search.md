# SearchHandlers

[**Router-файл пользовательского поиска объявлений**]()

> Минимальный MVP-поиска.
>
>Сознательно не включили:
>* ❌ фильтры по цене / категории / городу
>* ❌ умная релевантность
>* ❌ сохранённые поиски
>* ❌ история запросов
>* ❌ “похожие объявления”


> На будущее:
> - `ALL_CATEGORY_CB = "search_all"`: Поиску **[по всем категориям]()** - `search_in_all_categories()`
>   - Показываем популярные объявления из разных категорий
> - `"search_by_name"`: Выбран **[поиск по названию]()** - `search_by_name()`
> - `SEARCH_CITY_CB = "search_by_city"`: Выбран **[поиск по городу]()** - `process_search_by_city()`
> - `SEARCH_FILTERS_CB = "search_filters"`: Выбраны **[фильтры поиска]()** - `process_search_filters()`
> - **[Поиск имени подкатегории по ID]()** - `get_subcategory_name_by_id()`
>
> `search_text` = ("🔎 <b>Поиск по названию</b>\n\n Введите название вещи, которую хотите найти.\n 
> Например: 'палатка', 'велосипед', 'дрель'...\n\n Вы можете искать по любым ключевым словам.")

> `update_data: "search_query", "search_page"`

### Методы:

> `start_search` - **[Запускает поиск и запрашивает поисковый текст]()**
> * Принимает: `message`
>
> Срабатывает на:
>    - `/search`
>    - текст `🔎 Поиск`
>
> Внутри: вызывает `prompt_search_query(...)`

> `request_new_query` - **[Запрашивает новый поисковый текст]()**
> * Принимает: `callback`
>
> Срабатывает на: callback `search:new_query`
>
> Внутри:
>    - закрывает callback
>    - вызывает `prompt_search_query(...)`


> `prompt_search_query` - **[Запрашивает поисковый запрос у пользователя]()**
>
> Внутри:
>    - переводит FSM в `SearchStates.waiting_for_query`
>    - сбрасывает: `search_query` и `search_page`
>    - "Введите текст запроса:"
>
> Инвариант: если просим запрос — мы в `waiting_for_query` и query сброшен

> `process_search_query` - **[Обрабатывает поисковый запрос пользователя]()**
> * Принимает: `message`
>
> Срабатывает в:
>    - `SearchStates.waiting_for_query`
>    - только на `F.text`
>
> Внутри:
>    - нормализует текст
>    - валидирует
>    - если запрос корректный: `search_query` и `search_page=1`
>      - переводит FSM в `SearchStates.browsing`
>      - показывает первую страницу результатов


> `paginate_search` - **[Показывает другую страницу результатов поиска]()**
> * Принимает: `callback`
>
> Срабатывает на: callback `search:page:{page}`
>
> Внутри:
>    - парсит page
>    - если page корректная: показывает результаты


> `show_search_results` - **[Показывает страницу результатов поиска]()**
> * Принимает: `page`
>
> Внутри:
>    - читает из FSM: `search_query` и `search_page`
>    - если запрос есть: загружает страницу
>      - сохраняет текущую страницу в FSM
>      - обновляет экран


### Helper-функции:

> `normalize_search_query` - **[Нормализует поисковый запрос]()**

> `validate_search_query` - **[Проверяет длину поискового запроса]()**

> `parse_search_page` - **[Парсит номер страницы из callback data]()**

> `build_search_prompt_text` - **[Формирует prompt ввода запроса]()**

> `fetch_search_page` - **[Загружает страницу результатов поиска через ItemService]()**
> - `items[:PAGE_SIZE]` - если пришло 9 → показываем первые 8

> `build_search_results_text` - **[Формирует текст результатов поиска]()**

> `build_search_prompt_keyboard` - **[Собирает keyboard prompt-экрана поиска]()**


> Клава `build_search_keyboard`:
>* 🔎 Открыть `#{item.id}` - `"show_item_details:{item.id}"`
>* ⬅️ Пред - `"search:page:{page - 1}"`
>* ➡️ След - `"search:page:{page + 1}"`
>* ✏️ Новый запрос - `"search:new_query"`
>* 🔙 Назад - `"search:back"` / `"back_to_main_menu"`
>
> На будущее: `"back_to_results"` - Возвращаемся к результатам поиска
