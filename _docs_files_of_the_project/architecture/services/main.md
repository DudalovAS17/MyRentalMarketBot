# Документация по сервисам проекта

Документ описывает актуальный слой `services/`: какие репозитории использует каждый сервис, какие DTO возвращает, где живёт бизнес-логика и как работает `strict`.

Текущий проект — Telegram-бот компании по аренде товаров:
- каталог товаров ведут сотрудники компании;
- клиент создаёт заявку на аренду товара;
- менеджер/админ обрабатывает заявку;
- поддержка работает через тикеты;
- audit-действия сотрудников пишутся отдельно.

Сервисы — это слой между handlers/middleware и repositories. Repositories возвращают ORM-модели, а сервисы обычно возвращают Pydantic `Out` DTO.

---

## 0. Общие правила сервисного слоя

### Что делают сервисы

- Забирают ORM из repositories.
- Валидируют бизнес-условия.
- Конвертируют ORM в `...Out` DTO через `model_validate(...)`.
- Решают, когда вернуть `None/False`, а когда выбросить доменную ошибку.
- Координируют несколько репозиториев/сервисов, если это нужно для бизнес-инварианта.

### Что сервисы не должны делать

- Не должны создавать SQLAlchemy sessions.
- Не должны напрямую работать с Telegram event-объектами (`Message`, `CallbackQuery`).
- Не должны хранить FSM state.
- Не должны возвращать ORM наружу, кроме внутренних helper-методов, где это явно указано.

---

## 1. Что такое `strict`

`strict` — флаг режима строгости метода.

Он определяет поведение, если объект не найден, переход запрещён или операция не была выполнена.

### `strict=False`

Мягкий режим:
- объект не найден → `None`;
- действие не выполнено → `False` или `None`;
- вызывающий handler сам решает, какой UX показать.

Пример:
- `category = await category_service.get_category(123, strict=False)`
- [Если категории нет](), результат будет `None`

### `strict=True`

Жёсткий режим:
- объект не найден → `NotFoundError`;
- действие запрещено конфликтом статусов/инвариантов → `ConflictError`;
- нет прав → `ForbiddenError`;
- невалидный ввод → `ValidationError`.

Пример
- `category = await category_service.get_category(123, strict=True)`
- [Если категории нет](), будет [не]() `None`, а [**ошибка**]().

### Зачем это нужно

Один сервисный метод можно использовать в двух сценариях:
- в UI-flow, где удобнее мягко вернуть `None` или `False` и показать alert;
  - и дальше уже вызывающий код сам решит, что делать.
- во внутреннем use-case, где отсутствие объекта — ошибка сценария и лучше сразу бросить исключение.
  - и не писать одну и ту же проверку вручную каждый раз

---

## 2. `CategoryService`

Файл: `services/category_service.py`.

Сервис для категорий и подкатегорий каталога.

### Зависимости

- `CategoryRepository`.

### DTO helpers

- `_to_out(category) -> CategoryOut`.
- `_to_out_list(categories) -> list[CategoryOut]`.

### Методы

> `list_main_categories() -> list[CategoryOut]` - Возвращает корневые активные категории.

> `list_subcategories(category_id, strict=False) -> list[CategoryOut]`
- Если `strict=True`, сначала проверяет существование родительской категории.
- Если родитель не найден и `strict=True` — `NotFoundError`.
- Затем возвращает список подкатегорий.
- В мягком режиме пустой список может значить «нет подкатегорий» или «родитель не найден».

> `get_category_by_id(category_id, strict=False) -> Optional[CategoryOut]`
- Возвращает категорию по ID.
- При отсутствии: `None` или `NotFoundError`.

> `create(name, emoji=None, parent_id=None) -> CategoryOut`
- Создаёт категорию/подкатегорию.
- Перед созданием проверяет дубль имени внутри родителя через `exists_by_name_within_parent(...)`.
- Если дубль есть — `ConflictError`.

> `delete(category_id, strict=False) -> bool`
- Удаляет категорию.
- Если не нашли: `False` или `NotFoundError`.

### Важно

В сервисе сейчас нет `update`. Хотя `CategoryUpdate` в схемах есть, репозиторий/сервисный метод обновления категории в актуальном коде не реализован.

---

## 3. `ItemService`

Файл: `services/item_service.py`.

Сервис товаров каталога компании. Это не объявления пользователей.

### Зависимости

- `ItemRepository`.
- `RentalService` — нужен для проверки открытых заявок перед удалением/скрытием/архивацией товара.

### DTO helpers

- `_to_out(item) -> ItemOut`.
- `_to_out_list(items) -> list[ItemOut]`.

### Read methods

> `list_all_items(available_only=True, limit=None, offset=0) -> list[ItemOut]`
- Возвращает товары каталога.
- `available_only=True` превращается в репозитории в `active_only=True`, то есть фильтр `ItemStatus.ACTIVE`.

> `get_item_by_id(item_id, strict=False) -> Optional[ItemOut]`
- Возвращает товар по ID.
- При отсутствии: `None` или `NotFoundError`.

> `list_items_by_category(category_id, available_only=True) -> list[ItemOut]`
- Товары категории.

> `list_items_by_subcategory(subcategory_id, available_only=True) -> list[ItemOut]`
- Товары подкатегории.

> `list_items_by_created_admin_id(admin_id, available_only=False) -> list[ItemOut]`
- Товары, созданные сотрудником.

> `list_items_by_updated_admin_id(admin_id, available_only=False) -> list[ItemOut]`
- Товары, последний раз обновлённые сотрудником.

> `search_items(query, available_only=True, limit=50, offset=0) -> list[ItemOut]`
- Если query пустой после `strip()` — возвращает `[]`.
- Иначе ищет по каталогу через репозиторий.

> `list_item_characteristics_by_item_id(item_id, limit=None) -> list[ItemCharacteristicOut]`
- Возвращает характеристики товара в порядке `sort_order ASC, id ASC`.

### Write methods

> `create(item_data, created_by_admin_id=None, status=ItemStatus.DRAFT) -> ItemOut`
- Создаёт товар каталога компании.
- По умолчанию статус `DRAFT`.
- Пишет `created_by_admin_id`, если передан.

> `update(item_id, update_data, updated_by_admin_id=None, strict=False) -> Optional[ItemOut]`
- Обновляет товар.
- Пишет `updated_by_admin_id`, если были реальные изменения и параметр передан.
- При отсутствии товара: `None` или `NotFoundError`.

> `delete(item_id, strict=False) -> bool`
- Перед удалением проверяет открытые заявки через `rental_service.has_open_rentals_for_item(item_id)`.
- Если есть открытые заявки: `False` или `ConflictError`.
- Если товара нет: `False` или `NotFoundError`.

### Admin item logic

> `admin_list_drafts(page) -> tuple[list[ItemOut], bool]`
- Возвращает товары в статусе `DRAFT`.
- Работает через `admin_list_by_status(...)`.

> `admin_list_by_status(status, page) -> tuple[list[ItemOut], bool]`
- Пагинация по 8 элементов.
- Запрашивает `page_size + 1`, чтобы вычислить `has_next`.

> `admin_set_status(item_id, new_status, updated_by_admin_id=None, strict=False) -> Optional[ItemOut]`
- Загружает текущий товар.
- Если статус уже такой же — возвращает текущий DTO.
- Проверяет переход через `status.item_status.can_transition(...)`.
- Для `HIDDEN` и `ARCHIVED` проверяет отсутствие открытых заявок.
- Если всё ок — вызывает `item_repo.set_status(...)`.

---

## 4. `RentalService`

Файл: `services/rental_service.py`.

Клиентский сервис заявок на аренду товара компании.

### Зависимости

- `RentalRepository`.

### DTO helpers

- `_to_out(rental) -> RentalOut`.
- `_to_out_list(rentals) -> list[RentalOut]`.
- `_to_details(rental) -> RentalDetailsOut` — собирает `rental`, `item`, `user`.

### Business validation

> `_validate_transition(old_status, new_status, strict) -> bool`
- Проверяет переход через `status.rental_status.can_transition(...)`.
- При запрете: `False` или `ConflictError`.

### Read methods

> `get_by_id(rental_id, strict=False) -> Optional[RentalOut]`
- Заявка по ID.

> `list_rentals_by_user(user_id) -> list[RentalOut]`
- Все заявки клиента.
- Старых ролей owner/renter нет.

> `get_rental_details(rental_id, current_user_id, strict=False) -> Optional[RentalDetailsOut]`
- Загружает заявку с товаром и пользователем.
- Доступ разрешён только клиенту, которому принадлежит заявка (`rental.user_id == current_user_id`).
- Если доступа нет: `None` или `ForbiddenError`.

### Write/status methods

> `create(data: RentalCreate) -> RentalOut`
- Создаёт новую заявку клиента.
- Не валидирует старые `start_date/end_date`, потому что они сейчас не активны.

> `update(rental_id, data, strict=False) -> Optional[RentalOut]`
- Обновляет заявку.
- В комментарии к коду отмечено, что нужно осмыслить, стоит ли разрешать это клиенту.

> `cancel_by_client(rental_id, user_id, strict=False) -> bool`
- Клиент отменяет свою заявку.
- Проверяет, что заявка существует.
- Проверяет, что `rental.user_id == user_id`.
- Целевой статус: `RentalStatus.CANCELLED_BY_CLIENT`.
- Если статус уже `CANCELLED_BY_CLIENT` — возвращает `True`.
- Проверяет переход через `can_transition(...)`.
- Делает атомарное обновление через `repo.try_update_status_if_user(...)`.

### Availability methods

> `_get_open_rental_for_item(item_id)`
- Внутренний helper.
- Возвращает ORM-модель первой открытой заявки или `None`.
- Использует `repo.list_recent_open_by_item_id(...)` и `is_open_status(...)`.

> `get_open_rental_for_item(item_id) -> Optional[RentalOut]`
- Публичный DTO-метод для первой открытой заявки по товару.

> `ensure_item_available(item_id) -> None`
- Если по товару есть открытая заявка — выбрасывает `ItemNotAvailable`.
- Используется перед созданием новой заявки/проверкой доступности товара.

> `has_open_rentals_for_item(item_id) -> bool`
- Быстрая проверка наличия открытых заявок по товару.
- Используется `ItemService`.

---

## 5. `AdminRentalService`

Файл: `services/admin_rental_service.py`.

Админский сервис просмотра и обработки клиентских заявок.

### Зависимости

- `RentalRepository`.
- `AdminActionService` — пишет audit-log после смены статуса.

### DTO helpers

- `_to_rental_out(rental) -> RentalOut`.
- `_to_admin_details(rental) -> RentalAdminDetailsOut`.
- `_to_admin_details_list(rentals) -> list[RentalAdminDetailsOut]`.

### Business validation

> `_validate_non_empty_text(value, field_name) -> str`
- Нормализует обязательный текст.

> `_ensure_status_transition(old_status, new_status, strict) -> bool`
- Проверяет переход статуса заявки через `can_transition(...)`.

> `_validate_required_reason(status, comment) -> None`
- Для `REJECTED` и `CANCELLED_BY_ADMIN` требует причину.

### Read methods

> `list_recent_rentals(page) -> tuple[list[RentalAdminDetailsOut], bool]`
- Админский список последних заявок.
- Пагинация по 8 элементов.
- Загружает детали через `repo.list_recent_with_details_for_admins(...)`.

> `get_details(rental_id, strict=False) -> Optional[RentalAdminDetailsOut]`
- Детальная карточка заявки для сотрудника.

### Admin status methods

> `admin_set_status(rental_id, admin_tg_id, new_status, manager_comment=None, strict=False) -> Optional[RentalOut]`
- Основной метод смены статуса заявки сотрудником.
- Загружает заявку.
- Если статус не меняется — возвращает текущий DTO.
- Проверяет переход через `can_transition(...)`.
- Для негативных решений требует причину.
- Делает атомарный update через `repo.try_update_status(...)`.
- После успеха пишет audit через `AdminActionService.log_action(...)`.

> `take_in_progress(rental_id, admin_tg_id, strict=False)`
- `REQUESTED -> IN_PROGRESS`.

> `confirm_rental(rental_id, admin_tg_id, manager_comment=None, strict=False)`
- `REQUESTED/IN_PROGRESS -> CONFIRMED`.

> `reject_rental(rental_id, admin_tg_id, reason, strict=False)`
- `REQUESTED/IN_PROGRESS -> REJECTED`.
- Причина обязательна.

> `admin_cancel_rental(rental_id, admin_tg_id, reason, strict=False)`
- `CONFIRMED -> CANCELLED_BY_ADMIN`.
- Причина обязательна.

> `complete_rental(rental_id, admin_tg_id, manager_comment=None, strict=False)`
- `CONFIRMED -> COMPLETED`.

### Audit payload

При смене статуса пишется:
- `from_status`;
- `to_status`;
- `manager_comment`.

`action_type` выбирается через `admin_action_for_rental_status(new_status)`, `entity_type=AdminEntityType.RENTAL`.

---

## 6. `UserService`

Файл: `services/user_service.py`.

Сервис клиентов, регистрации, доступа и админской блокировки.

### Вспомогательные типы

> `StartAction`
- `REGISTER` — нужно зарегистрировать.
- `NEED_PHONE` — пользователь есть, но нет телефона.
- `ACCESS_BLOCKED` — аккаунт заблокирован.
- `MAIN_MENU` — можно показывать главное меню.

> `StartEntryResult`
- `action: StartAction`.
- `user: UserOut | None`.

> `can_use_bot(status) -> bool`
- Сейчас `True` только для `AccountStatus.ACTIVE`.

### Зависимости

- `UserRepository`.
- `admin_ids: FrozenSet[int]` — whitelist сотрудников для запрета бана админа.

### Методы чтения

- `get_by_id(user_id, strict=False)`.
- `get_by_telegram_id(telegram_id, strict=False)`.
- `list_all(limit=None, offset=0)`.
- `list_by_account_status(status, limit=None, offset=0)`.

Все возвращают `UserOut` или список `UserOut`.

### Write methods

> `create(user_data) -> UserOut`
- Валидирует `telegram_id > 0`.
- Создаёт клиента.

> `update(user_id, update_data, strict=False) -> Optional[UserOut]`
- Обновляет профиль клиента.

> `delete(user_id, strict=False) -> bool`
- Физически удаляет клиента.
- Для продукта чаще безопаснее использовать бан.

> `register_or_update_user(user_data) -> UserOut`
- Если пользователь с `telegram_id` есть — обновляет профиль без `telegram_id`.
- Если не найден — создаёт.
- Используется для входа/регистрации.

### Admin-user logic

> `ban_user(user_id, reason, admin_telegram_id, banned_by_admin_id=None, strict=False) -> Optional[UserOut]`
- Требует непустую причину.
- Нельзя забанить сотрудника из `admin_ids`.
- Нельзя забанить самого себя.
- Проверяет переход `ACTIVE -> BANNED` через `can_transition(...)`.
- Пишет `banned_at`, `banned_by_admin_id`, `ban_reason`.

> `unban_user(user_id, strict=False) -> Optional[UserOut]`
- Проверяет переход `BANNED -> ACTIVE`.
- Очищает `banned_at`, `banned_by_admin_id`, `ban_reason`.

### Client access

> `check_user_exists(telegram_id) -> bool`
- Проверяет наличие клиента.

> `is_user_blocked(telegram_id, strict=False) -> Optional[bool]`
- Возвращает `True/False`, либо `None`, если пользователь не найден и `strict=False`.

> `resolve_start_entry(telegram_id) -> StartEntryResult`
- Решает, что делать на `/start`:
  - нет пользователя → `REGISTER`;
  - заблокирован → `ACCESS_BLOCKED`;
  - нет телефона → `NEED_PHONE`;
  - всё хорошо → `MAIN_MENU`.

---

## 7. `AdminDirectoryService`

Файл: `services/admin_directory_service.py`.

Сервис профилей сотрудников компании.

### Зависимости

- `AdminRepository`.

### Методы

> `get_by_telegram_id(telegram_id, strict=False) -> Optional[AdminOut]`
- Возвращает сотрудника по Telegram ID.
- При отсутствии: `None` или `NotFoundError`.

> `sync_admins_from_settings(admin_ids: set[int]) -> None`
- Идемпотентно создаёт профили сотрудников для Telegram ID из настроек.
- `ADMIN_IDS` остаётся источником доступа, а sync нужен, чтобы FK/audit могли найти внутренний `admins.id`.
- Если `admin_ids` пустой — пишет warning и ничего не создаёт.

---

## 8. `AdminActionService`

Файл: `services/admin_service.py`.

Сервис чтения и записи audit-действий сотрудников.

### Зависимости

- `AdminActionRepository`.

### Helpers / validation

- `_enum_to_str(value)` — enum -> `.value`, иначе `str(value)`.
- `_validate_admin_tg_id(admin_tg_id)` — ID должен быть положительным.
- `_validate_admin_id(admin_id)` — ID должен быть положительным.
- `_validate_required_text(value, field_name)` — обязательный непустой текст.

### Read methods

- `list_recent(limit=None, offset=0) -> list[AdminActionOut]`.
- `list_by_admin_tg_id(admin_tg_id, limit=None, offset=0) -> list[AdminActionOut]`.
- `list_by_admin_id(admin_id, limit=None, offset=0) -> list[AdminActionOut]`.
- `list_by_entity(entity_type, entity_id, limit=None, offset=0) -> list[AdminActionOut]`.

`entity_type` и `action_type` могут быть enum-ами или строками; сервис нормализует их к строкам.

### Write methods

> `log_action(admin_tg_id, action_type, entity_type, entity_id, admin_id=None, note=None, payload=None) -> AdminActionOut`
- Валидирует `admin_tg_id`.
- Нормализует `action_type`, `entity_type`, `entity_id` в непустые строки.
- Создаёт audit-запись.

---

## 9. `PhotoService`

Файл: `services/photo_service.py`.

Сервис фотографий товаров каталога.

### Зависимости

- `PhotoRepository`.

### Методы

> `get_photos_by_item_id(item_id) -> list[PhotoOut]`
- Все фото товара.

> `get_photo_by_id(photo_id, strict=False) -> Optional[PhotoOut]`
- Фото по ID.

> `create_photo(item_id, telegram_file_id) -> PhotoOut`
- Создаёт одно фото по Telegram `file_id`.
- `sort_order` берётся как текущее количество фото товара.
- Если это первое фото — `is_main=True`.

> `create_photos(item_id, file_ids) -> list[PhotoOut]`
- Массово создаёт фото.
- Если список пустой — `[]`.
- Считает начальный `sort_order` от текущего количества фото.
- Первое фото станет главным только если до этого фото у товара не было.

> `delete_photo(photo_id, strict=False) -> bool`
- Удаляет фото.
- После удаления вызывает `repo.reorder(item_id)`.
- Сейчас если удалили главное фото, сервис не назначает новое главное автоматически.

> `move_photo(photo_id, direction, strict=False) -> bool`
- `direction`: `up` или `down`.
- Использует `repo.swap_with_neighbor(...)`.
- Если фото крайнее или не найден сосед — `False` или `ConflictError`.

> `set_order(photo_id, new_order, strict=False) -> bool`
- Перемещает фото на конкретную позицию внутри товара.
- Сначала загружает фото, чтобы узнать `item_id`.

---

## 10. `ReviewService`

Файл: `services/review_service.py`.

Сервис отзывов клиентов.

### Зависимости

- `ReviewRepository`.
- `RentalRepository` — нужен для проверки заявки перед созданием отзыва.

### Validation helpers

> `_ensure_rental_completed(status)`
- Отзыв можно оставить только если заявка `RentalStatus.COMPLETED`.

> `_ensure_actor_is_rental_user(rental_user_id, actor_id)`
- Отзыв может оставить только клиент, которому принадлежит заявка.

> `_ensure_review_not_exists(rental_id, user_id)`
- Проверяет, что клиент ещё не оставлял отзыв по этой заявке.
- Иначе `ConflictError`.

### Read methods

- `get_by_id(review_id, strict=False) -> Optional[ReviewOut]`.
- `list_reviews_by_rental(rental_id) -> list[ReviewOut]`.
- `list_reviews_by_user(user_id) -> list[ReviewOut]`.
- `list_reviews_by_item(item_id, published_only=True) -> list[ReviewOut]`.

### Write methods

> `create_review(actor_id, data: ReviewCreate) -> Optional[ReviewOut]`
- Загружает заявку через `rental_repo.get_by_id(...)`.
- Если заявки нет — `NotFoundError`.
- Проверяет, что заявка завершена.
- Проверяет, что actor — владелец заявки (`rental.user_id`).
- Проверяет, что отзыв по этой заявке ещё не существует.
- Создаёт `ReviewCreateInternal(user_id=actor_id, ...)`.
- Возвращает `ReviewOut`.

### Важно

Отзыв в текущей модели не содержит `reviewee_id`: это отзыв клиента по заявке/товару компании, а не отзыв одного пользователя о другом в marketplace.

---

## 11. `SupportService`

Файл: `services/support_service.py`.

Сервис обращений клиентов в поддержку.

### Зависимости

- `SupportTicketRepository`.

### Helpers / validation

- `_page_window(page, page_size=8) -> (limit, offset)`.
- `_ensure_user_has_no_open_ticket(user_id)` — если есть открытый тикет, бросает `TicketAlreadyOpen`.

### Read methods

> `get_ticket_by_id(ticket_id, strict=False) -> Optional[SupportTicketOut]`
- Тикет по ID.

> `list_open_tickets(page) -> tuple[list[SupportTicketOut], bool]`
- Открытые тикеты с пагинацией по 8.
- Запрашивает `limit + 1` для `has_next`.

> `get_open_ticket_by_user(user_id, strict=False) -> Optional[SupportTicketOut]`
- Открытый тикет клиента, если есть.

### Write/admin methods

> `create(ticket_data: SupportTicketCreateInternal) -> SupportTicketOut`
- Перед созданием проверяет, что у клиента нет открытого тикета.
- Если есть — `TicketAlreadyOpen`.

> `close_ticket_by_admin(ticket_id, closed_by_admin_id=None, strict=False) -> bool`
- Закрывает тикет через репозиторий.
- Если тикет не найден или уже закрыт: `False` или `ConflictError`.

> `mark_admin_replied(ticket_id, strict=False) -> bool`
- Ставит timestamp последнего ответа администратора.
- Если тикет не найден: `False` или `NotFoundError`.

---

## 12. `NotificationService`

Файл: `services/notif_service.py`.

Сервис безопасной отправки Telegram-уведомлений.

### Вспомогательный DTO

> `NotificationResult`
- `chat_id: int | str`;
- `success: bool`;
- `error: Optional[str]`.

### Базовые методы

> `normalize_text(text) -> str`
- `strip()`.
- Если текст пустой — `ValueError`.

> `send_message(chat_id, text, reply_markup=None, parse_mode="HTML") -> NotificationResult`
- Не пробрасывает Telegram API ошибки наружу.
- Ловит:
  - `TelegramRetryAfter`;
  - `TelegramBadRequest`;
  - `TelegramForbiddenError`;
  - `TelegramAPIError`.
- Возвращает `NotificationResult(success=False, error=str(exc))`.

> `send_to_user(telegram_id, text, reply_markup=None) -> bool`
- Отправляет одному пользователю.

> `notify_user(...)`
- Backward-compatible alias для `send_to_user`.

> `notify_users(user_ids, text, reply_markup=None) -> list[NotificationResult]`
- Массовая отправка с подробным результатом по каждому chat_id.

> `send_to_admins(admin_ids, text, reply_markup=None) -> dict[int | str, bool]`
- Массовая отправка админам из `ADMIN_IDS`.

### Domain notification methods

- `notify_admins_new_rental(...)`.
- `notify_user_rental_created(...)`.
- `notify_user_rental_status_changed(...)`.
- `notify_user_rental_cancelled(...)`.
- `notify_admins_client_cancelled_rental(...)`.
- `notify_admins_new_support_ticket(...)`.
- `notify_user_support_ticket_created(...)`.
- `notify_user_support_reply(...)`.
- `notify_user_support_ticket_closed(...)`.

Форматирование текстов находится в `handlers/notification.py`, а сервис только отправляет готовый текст и безопасно обрабатывает Telegram API ошибки.

---

## 13. Исключения и доменные ошибки

Сервисы используют ошибки из `utils.errors` и `utils.domain_exceptions`.

Типичные ошибки:
- `NotFoundError` — сущность не найдена при `strict=True`.
- `ConflictError` — запрещённый переход статуса или конфликт бизнес-инварианта.
- `ForbiddenError` — нет доступа к чужой заявке / нельзя забанить себя или сотрудника.
- `ValidationError` — невалидный текст/ID/причина.
- `ServiceError` — общая сервисная ошибка.
- `ItemNotAvailable` — товар нельзя арендовать из-за открытой заявки.
- `TicketAlreadyOpen` — у клиента уже есть открытый тикет поддержки.

---

## 14. Практические правила для разработки

1. **Сервис возвращает DTO, не ORM.** Исключение — внутренние helper-методы вроде `_get_open_rental_for_item(...)`.
2. **Business checks должны жить в сервисе, не в repository.** Repository делает DB-операции, сервис решает, можно ли их делать.
3. **Для переходов статусов использовать `can_transition(...)`.** Это касается товаров, заявок и аккаунтов.
4. **При операциях с товаром учитывать открытые заявки.** Удаление/скрытие/архивация товара должны проходить через `RentalService.has_open_rentals_for_item(...)`.
5. **Admin-действия, меняющие заявку, должны писать audit-log.** Это делает `AdminRentalService` через `AdminActionService`.
6. **Не возвращать Telegram API exceptions из notification service.** Уведомления не должны ломать основной бизнес-flow.
7. **Не возвращать старые owner/renter сценарии в сервисы.** Актуальная модель: клиентская заявка в компанию.
