# Admin — административная панель

Раздел описывает актуальные административные handlers. Админка предназначена для сотрудников компании: управление заявками на аренду, тикетами поддержки, товарами каталога и клиентами.

---

## 1. Карта файлов

| Файл                                                            | Назначение                                                                           |
|-----------------------------------------------------------------|--------------------------------------------------------------------------------------|
| `handlers/admin/__init__.py`                                    | Собирает общий `admin_router` из подроутеров.                                        |
| `handlers/admin/menu.py`                                        | Точка входа `/admin`, главное меню и выход.                                          |
| `handlers/admin/deals.py`                                       | Список заявок на аренду, карточка заявки, поиск заявки по ID.                        |
| `handlers/admin/deals_status_actions.py`                        | Смена статусов заявки администратором.                                               |
| `handlers/admin/support.py`                                     | Админская поддержка: список тикетов, карточка, ответ, закрытие.                      |
| `handlers/admin/users_moderation.py`                            | Поиск клиента, карточка клиента, бан/разбан.                                         |
| `handlers/admin/items_moderation.py`                            | Списки товаров по статусу и status-actions товара.                                   |
| `handlers/admin/create_item.py`                                 | Создание товара сотрудником через FSM.                                               |
| `handlers/admin/update_item.py`                                 | Черновой старт редактирования товара, полноценное редактирование ещё не реализовано. |
| `handlers/admin/admin_helpers/*`                                | Клавиатуры, тексты, парсеры и функции показа карточек/списков.                       |
| `handlers/admin/create_item_helpers/*`                          | Helpers создания товара: тексты, клавиатуры, загрузка, валидация, сохранение draft.  |
| `handlers/admin/trash.py`, `handlers/admin/cre_item_helpers.py` | Старый/неиспользуемый код, не считать источником актуальной логики.                  |

---

## 2. Состав `admin_router`

В общий роутер включены:

1. `admin_menu_router`;
2. `admin_deals_router`;
3. `admin_support_router`;
4. `admin_items_router`;
5. `admin_users_router`;
6. `admin_status_actions_router`;
7. `admin_create_item_router`;
8. `admin_update_item_router`.

Доступ к `admin_router` защищается middleware `AdminCheckMiddleware`, поэтому handlers внутри админки не должны вручную повторять базовую проверку роли на каждом callback-е.

---

## 3. Главное меню админки

`show_admin_menu()` срабатывает на:

- команду `/admin`;
- callback `admin:menu`.

Показывает текст `ADMIN_MENU_TEXT` и клавиатуру `get_admin_menu_keyboard()`.

`admin_exit()` по callback `admin:exit` показывает сообщение о выходе и клавиатуру возврата.

---

## 4. Заявки на аренду: `deals.py`

### Список заявок

`admin_deals_list()` открывается по `DEALS_PREFIX` (`admin:deals`) и показывает первую страницу списка через `show_deals_list()`.

`admin_deals_page()` обрабатывает пагинацию `DEALS_PAGE_PREFIX + page`.

### Карточка заявки

`admin_deals_view()` открывает карточку по `DEALS_VIEW_PREFIX + rental_id`.

Карточка строится из `RentalAdminDetailsOut` и содержит клиентские/товарные данные, статус и action-кнопки, зависящие от статуса.

### Поиск по ID

`admin_deals_open_by_id()` ставит `AdminStates.waiting_rental_id` и просит ввести ID.

`admin_deals_process_id()`:

- парсит число;
- при ошибке остаётся в состоянии;
- при успехе очищает FSM;
- показывает карточку заявки.

---

## 5. Status-actions заявки: `deals_status_actions.py`

Поддерживаемые действия:

| Callback prefix         | Обработчик                                                | Сервисный метод               | Назначение                                 |
|-------------------------|-----------------------------------------------------------|-------------------------------|--------------------------------------------|
| `DEALS_PROGRESS_PREFIX` | `admin_deals_take_in_progress()`                          | `take_in_progress()`          | Взять заявку в работу.                     |
| `DEALS_CONFIRM_PREFIX`  | `admin_deals_confirm()`                                   | `confirm_rental()`            | Подтвердить заявку.                        |
| `DEALS_COMPLETE_PREFIX` | `admin_deals_complete()`                                  | `complete_rental()`           | Завершить аренду.                          |
| `DEALS_REJECT_PREFIX`   | `admin_deals_reject_ask()` → `admin_deals_reject_apply()` | `reject_rental()`             | Отклонить заявку с причиной.               |
| `DEALS_CANCEL_PREFIX`   | `admin_deals_cancel_ask()` → `admin_deals_cancel_apply()` | `cancel_confirmed_by_admin()` | Отменить подтверждённую аренду с причиной. |

После успешной смены статуса handler:

- уведомляет клиента через `NotificationService`;
- перерисовывает карточку заявки;
- показывает результат администратору.

Для действий с причиной используется FSM:

- `AdminStates.waiting_rental_reject_reason`;
- `AdminStates.waiting_rental_cancel_reason`;
- временный ключ `rental_id`.

---

## 6. Админская поддержка: `support.py`

### Список и карточка

- `admin_support_list()` — первая страница открытых тикетов;
- `admin_support_list_page()` — пагинация;
- `admin_support_view()` — карточка тикета.

Список строится через `show_support_ticket_list()`, карточка — через `show_support_ticket_card_or_not_found()`.

### Ответ пользователю

1. `admin_support_reply_prompt()` проверяет, что тикет открыт, ставит `AdminSupportStates.waiting_reply_text`, сохраняет `ticket_id`.
2. `admin_support_reply_send()` загружает тикет и пользователя, проверяет непустой текст.
3. `send_support_reply_and_audit()` отправляет ответ и пишет audit.
4. Только после успешной доставки вызывается `support_service.mark_admin_replied()`.
5. FSM очищается.

### Закрытие тикета

`admin_support_close()`:

- проверяет открытый тикет;
- загружает пользователя тикета;
- находит профиль сотрудника в `admins` через `AdminDirectoryService`;
- закрывает тикет через `support_service.close_ticket_by_admin()`;
- уведомляет пользователя и пишет audit;
- перерисовывает карточку.

---

## 7. Клиенты: `users_moderation.py`

| Вход                                  | Обработчик                   | Поведение                                    |
|---------------------------------------|------------------------------|----------------------------------------------|
| `admin:users`                         | `admin_users_menu()`         | Меню управления пользователями, очищает FSM. |
| `admin:users:view:<id>`               | `admin_users_view()`         | Карточка клиента.                            |
| `admin:users:find`                    | `admin_users_find()`         | Просит ввести `user_id`.                     |
| `AdminStates.waiting_user_id`         | `admin_users_find_message()` | Парсит ID и показывает карточку.             |
| `admin:users:ban:<id>`                | `admin_users_ban_prompt()`   | Просит причину бана.                         |
| `AdminStates.waiting_user_ban_reason` | `admin_users_ban_apply()`    | Банит клиента с причиной.                    |
| `admin:users:unban:<id>`              | `admin_users_unban()`        | Разбанивает клиента.                         |

Бан вызывает `user_service.ban_user(..., admin_telegram_id=message.from_user.id)`, чтобы audit мог связать действие с сотрудником.

---

## 8. Товары: `items_moderation.py`

Админская модерация товаров работает со статусами `ItemStatus`.

| Callback                           | Обработчик              | Поведение                              |
|------------------------------------|-------------------------|----------------------------------------|
| `admin:items`                      | `admin_items_list()`    | Меню модерации товаров.                |
| `admin:items:filter:<status>`      | `admin_items_filter()`  | Список товаров по статусу, страница 1. |
| `admin:items:page:<status>:<page>` | `admin_items_page()`    | Пагинация.                             |
| `admin:items:view:<id>`            | `admin_items_view()`    | Карточка товара.                       |
| `admin:items:approve:<id>`         | `admin_items_approve()` | Перевод в `ACTIVE`.                    |
| `admin:items:hide:<id>`            | `admin_items_hide()`    | Перевод в `HIDDEN`.                    |
| `admin:items:unhide:<id>`          | `admin_items_unhide()`  | Возврат в `ACTIVE`.                    |
| `admin:items:archive:<id>`         | `admin_items_archive()` | Перевод в `ARCHIVED`.                  |

Status-action выполняется через `item_service.admin_set_status()`. Если переход запрещён, пользователь получает alert/сообщение, а карточка не меняется.

---

## 9. Helpers админки

- `admin_helpers/keyboard.py` — все inline-клавиатуры админки;
- `admin_helpers/parse.py` — парсинг ID, страниц и статусов;
- `admin_helpers/show.py` — единые функции показа списков/карточек;
- `admin_helpers/texts.py` — форматирование карточек заявок, товаров, клиентов и тикетов;
- `admin_helpers/file_support.py` — проверка открытого тикета, отправка ответа, уведомление о закрытии и audit.

---

## 10. Правила разработки

1. Новые разделы админки подключать в `handlers/admin/__init__.py` и добавлять кнопку в `admin_helpers/keyboard.py`.
2. Все изменения статусов заявок выполнять через admin service, чтобы сохранялись правила переходов и audit.
3. Для действий с причиной использовать FSM и очищать его только после получения валидного payload.
4. Не отправлять пользователю уведомление о поддержке как успешное, если доставка сообщения не удалась.
5. Не использовать файлы `trash.py` как актуальную логику.