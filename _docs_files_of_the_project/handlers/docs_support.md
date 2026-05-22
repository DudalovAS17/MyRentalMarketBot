# SupportHandlers

[**Router-файл пользовательского сценария обращения в поддержку**]()

### Методы:

> `support_start` - **[Запускает обращение в поддержку через команду]()**
> * Принимает: `message`
> * Срабатывает на: `/support`

> `support_start_callback` - **[Запускает обращение в поддержку через кнопку]()**
> * Принимает: `callback`
> * Срабатывает на: callback `support:start`
> 
> `(F.data.in_(["support:start", "profile_help"]))`

> `start_support_flow` - **[Начинает сценарий обращения в поддержку]()**
>
> Внутри:
>    - проверяет наличие открытого тикета
>    - если открытый тикет уже есть:
>      - показывает UX-сообщение
>      - не переводит FSM в ожидание текста
>    - если открытого тикета нет:
>      - переводит FSM в `SupportStates.waiting_text`
>      - показывает обращение в поддержку
>    - не даём создать второй OPEN тикет

> `receive_support_text` - **[Создаёт тикет поддержки и уведомляет админов]()**
> * Принимает: `message` / `admin_ids`
>
> Внутри:
>    - получает текст обращения
>    - если текст есть: создаёт `SupportTicketCreateInternal`
>
> Если service выбросил `TicketAlreadyOpen`:
>    - очищает FSM
>    - сообщает пользователю о существующем открытом тикете
>
> Если тикет создан:
>    - очищает FSM
>    - показывает confirmation пользователю
>    - уведомляет админов

> `cancel_support` - **[Отменяет обращение в поддержку]()**
> * Принимает: `callback`
>
> Внутри:
>    - очищает FSM
>    - показывает сообщение об отмене
>    - возвращает пользователя в главное меню
>
> Срабатывает на: callback `cancel:support` (`cancel_support`)

### Helper-функции:

> `build_support_request_text` - **[Формирует prompt обращения в поддержку]()**

> `build_support_cancel_keyboard` - **[Собирает клавиатуру отмены обращения]()**

> `build_support_confirmation_text` - **[Формирует confirmation после создания тикета]()**

> `build_support_cancelled_text` - **[Формирует текст отмены обращения]()**

> `build_support_empty_text_error` - **[Формирует ошибку пустого обращения]()**

> `build_support_already_open_text` - **[Формирует текст уже открытого тикета]()**

> `build_support_already_open_after_create_text` - **[Формирует текст ошибки `TicketAlreadyOpen`]()**

> `build_admin_ticket_message` - **[Формирует уведомление админам о новом тикете]()**

> `notify_admins_about_ticket` - **[Отправляет уведомление админам о новом тикете]()**