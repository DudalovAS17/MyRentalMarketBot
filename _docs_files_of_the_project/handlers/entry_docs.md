# Основа

>`Middleware гарантирует:`
>* пользователь существует
>* пользователь не заблокирован
>* телефон подтверждён
>* `user` уже загружен из БД и передан сюда

> `ServiceError` - бизнес-проблема: даём понятный UX-ответ (`send_reply`)
> 
> Если сервис не смог загрузить категории:
>* пользователю показывается короткий UX-ответ
>* `handler` завершает выполнение без traceback
>
> `return` (или `return await show_main_menu()` ???)


>Стоит ли там, где есть (...., `user`) делать (...., `user: UserOut`) ?

---

# Base entry

[**Для показа главного меню пользователя**]()

### Методы:

> `show_main_menu` - [Показывает главное меню]()

### На будущее:
- уведомления: "🔔 У вас {unread_notifications} непрочитанных уведомлений"
- активности пользователя: обновляем информацию о последней активности пользователя
- данные поиска: очищаем временные данные поиска

### Что использует:
- `build_main_menu_text(user)`
- `get_main_menu_keyboard(user)`
- `send_reply`

---

# Category entry

[**Для показа списка категорий**]()

- Сценарий поиска («🔍 Арендовать») ???

```
Функцию можно дергать как:
- reply-menu кнопку
- callback “назад”
- админка
```

### Методы:

> `show_categories` - [Показывает список корневых категорий]()
* если `event` — это `CallbackQuery`: вызывает `event.answer()`
* затем: 
    - получает категории (убрал `categories = categories or []`)
    - строит клавиатуру
    - отправляет ответ

### Что использует:
- `build_categories_screen_keyboard`
- `send_reply`
- `ServiceError`

---

# Item entry

[**Для показа списка объявлений пользователя**]()

```
- из reply-кнопки главного меню
- из callback "назад к моим объявлениям"
- после завершения item-flow
```

### Методы:

> `show_my_items` - [Показывает пользователю список его объявлений]()

* если `event` — это `CallbackQuery`: вызывает `event.answer()`
* затем: 
    - получает категории (убрал `items = items or []`)
    - строит клавиатуру
    - отправляет ответ

### Что использует:
- `my_items_screen_text`
- `build_my_items_keyboard`
- `send_or_edit`
- `send_reply`
- `ServiceError`

---

# Auth entry

[**Для сценария первичной регистрации нового пользователя**]()

```
Только сценарий НОВОГО пользователя:
- создаём запись
- просим контакт (телефон)

Никаких проверок блокировки/«уже зарегистрирован» — это задача /start.
```

### Методы:

убрал:
- `from schemas.user import UserOut`
- `from handlers.base import show_main_menu`

> `start_registration` - [Запускает первичную регистрацию нового пользователя]()

>Собирает `UserCreate` из Telegram-пользователя
> 
> Регистрирует пользователя (или получаем существующего?)
> 
>* `ServiceError`
>* Убрал `IntegrityError`: `⚠️ Аккаунт уже существует. Используйте /start для входа в меню.`
>
> После успешного создания пользователя просит пользователя поделиться телефоном

> [FSM перейдёт в состояние `PHONE_NUMBER` позже (в обработчике контакта)]() ???

### Что использует:
- `UserCreate`
- `build_registration_welcome_text`
- `build_registration_contact_keyboard`
- `IntegrityError`

---

# Rental entry

[**Entry-helper для показа списка сделок пользователя**]()

### Методы:

> `show_my_rentals` - [Показывает список сделок пользователя]()
>  * Используется для входа в экран:
>    - `📋 Мои сделки`
>    - callback `MY_RENTALS_CB`
>    - `"back_to_rentals"`

### Что использует:
- `build_empty_my_rentals_keyboard`
- `build_my_rentals_keyboard`

---

# Entry Helpers

> base:
>   * `build_main_menu_text`
> 
> category:
>   * `build_categories_screen_keyboard`
> 
> auth:
>   * `build_registration_contact_keyboard`
>   * `build_registration_welcome_text`
> 
> rental:
>   * `sort_rentals_for_list`
>   * `build_rental_list_button_text`
>   * `build_my_rentals_keyboard`
>   * `build_empty_my_rentals_keyboard`

---

## Rental entry helpers

> `build_empty_my_rentals_keyboard` - [Собирает клавиатуру для пустого списка сделок]()
>  * Используется, когда у пользователя ещё нет сделок
>  * Добавляет кнопку: `🏠 Главное меню`

> `build_my_rentals_keyboard` - [Собирает inline-клавиатуру списка сделок пользователя]()
>  * Принимает: `rentals` / `current_user_id` / `limit`
>  * Внутри:
>    - сортирует сделки через `sort_rentals_for_list(...)`
>    - ограничивает список через `limit`
>    - для каждой сделки создаёт кнопку деталей
>    - добавляет кнопку `🏠 Главное меню`
>  * Callback кнопки сделки ведёт на:
>    - `RENTAL_DETAILS_CB + rental.id`

> `sort_rentals_for_list` - [Сортирует сделки для отображения в списке]()
>  * Принимает: `rentals`
>  * Сортирует по правилу:
>    - сначала открытые / активные сделки
>    - затем остальные сделки
>    - внутри группы новые сделки выше старых
>  * Использует внутренний UI-набор статусов: `OPEN STATUS = active_first`

> `первая часть:`
>* 0, если статус `“активный=OPEN_STATUSES”` (`REQUESTED/CONFIRMED/ACTIVE/DISPUTED`)
>* 1, если статус `“не активный=TERMINAL_STATUSES”` (`COMPLETED/всякие CANCELLED/REJECTED…`)
>✅ При сортировке 0 идёт раньше 1, значит активные сделки будут сверху.
>
> `вторая часть: -id`
>* если `id` = 120 → ключ = -120
>* если `id` = 15 → ключ = -15
>
>✅ При сортировке по возрастанию -120 < -15, значит больший `id` окажется раньше.
> То есть внутри каждой группы ты получаешь самые новые сделки сверху (если `id` растёт).
>
> * `id=10, COMPLETED → (1, -10)`
> * `id=11, REQUESTED → (0, -11)`
> * `id=12, ACTIVE → (0, -12)`
> * `id=13, CANCELLED… → (1, -13)`


> `build_rental_list_button_text` - [Формирует текст кнопки одной сделки]()
>  * Принимает: `rental` / `current_user_id`
>  * Определяет роль текущего пользователя в сделке:
>    - `OWNER` → `"Владелец"`
>    - `RENTER` → `"Арендатор"`
>  * Добавляет в текст:
>    - `id` сделки
>    - роль пользователя
>    - статус сделки