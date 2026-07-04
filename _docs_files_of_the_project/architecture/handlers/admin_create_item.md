# Admin: create item  — создание товаров каталога

Документ описывает handler-логику товаров. В текущем проекте товар — позиция каталога компании для аренды. Создают и управляют товарами сотрудники через админку; клиенты только просматривают товары и создают заявки.

---

## 1. Какие файлы относятся к item handlers

| Файл                                             | Назначение                                                                            |
|--------------------------------------------------|---------------------------------------------------------------------------------------|
| `handlers/admin/create_item.py`                  | Полный FSM создания товара сотрудником.                                               |
| `handlers/admin/create_item_helpers/common.py`   | Нормализация ввода и форматирование чисел/денег/фото.                                 |
| `handlers/admin/create_item_helpers/keyboard.py` | Клавиатуры выбора категории/подкатегории, фото и подтверждения.                       |
| `handlers/admin/create_item_helpers/load.py`     | Загрузка сущностей, показ категорий, отправка preview, привязка фото.                 |
| `handlers/admin/create_item_helpers/store.py`    | Сохранение выбранных сущностей и edit-контекста в FSM.                                |
| `handlers/admin/create_item_helpers/texts.py`    | Тексты шагов создания, preview и успешного создания.                                  |
| `handlers/admin/create_item_helpers/validate.py` | Валидация title/description/price/quantity/min period.                                |
| `handlers/admin/items_moderation.py`             | Списки товаров по статусам и быстрые status-actions.                                  |
| `handlers/admin/update_item.py`                  | Черновой вход в редактирование товара; полноценное редактирование ещё не реализовано. |

---

## 2. FSM создания товара

Создание товара использует `ItemCreateStates`:

1. `category` — выбор основной категории;
2. `subcategory` — выбор подкатегории;
3. `title` — название товара;
4. `description` — описание;
5. `price` — цена;
6. `available_quantity` — доступное количество;
7. `rental_period` — минимальный срок аренды;
8. `photos` — загрузка фотографий;
9. `confirmation` — preview и публикация.

В FSM хранятся:

- `mode=ADMIN_CREATE_ITEM_MODE`;
- `admin_user_id`;
- `new_item` — сериализованный `ItemCreateDraft`;
- `photos` — список Telegram `file_id`;
- выбранные category/subcategory данные для UI.

---

## 3. Старт создания

`start_create_item_by_admin()` срабатывает по callback `ADMIN_ADD_ITEM_CB`.

Алгоритм:

1. подтверждает callback;
2. очищает старый FSM;
3. создаёт пустой `ItemCreateDraft`;
4. сохраняет режим создания, ID сотрудника и пустой список фото;
5. ставит `ItemCreateStates.category`;
6. показывает список основных категорий через `show_create_item_categories_step()`.

---

## 4. Выбор категории и подкатегории

### Категория

`show_subcategories_for_creating_item()` обрабатывает `ADMIN_CAT_FI_PREFIX + category_id`.

Он:

- загружает категорию;
- загружает подкатегории;
- сохраняет выбранную категорию в FSM;
- ставит `ItemCreateStates.subcategory`;
- показывает клавиатуру подкатегорий.

### Подкатегория

`start_create_item_from_subcategory()` обрабатывает `ADMIN_SUBCAT_FI_PREFIX + subcategory_id`.

Он:

- загружает подкатегорию и родительскую категорию;
- достаёт draft;
- записывает `category_id` и `subcategory_id`;
- сохраняет UI-контекст;
- переводит сценарий к вводу названия через `start_create_item_title()`.

---

## 5. Текстовые шаги создания

| State                | Обработчик                     | Валидация                            | Что сохраняется                                |
|----------------------|--------------------------------|--------------------------------------|------------------------------------------------|
| `title`              | `process_item_title()`         | `validate_item_title()`              | `draft.title`                                  |
| `description`        | `process_item_description()`   | `validate_item_description()`        | `draft.description`                            |
| `price`              | `process_item_price()`         | `validate_item_price()`              | `draft.price`, форматированный price text      |
| `available_quantity` | `process_item_quantity()`      | `validate_item_available_quantity()` | `draft.available_quantity`                     |
| `rental_period`      | `process_item_rental_period()` | `validate_item_min_period()`         | `draft.min_rental_period_days` / текст периода |

Если валидация не проходит, FSM остаётся на текущем шаге и пользователь получает текст ошибки.

---

## 6. Фото товара

Состояние `ItemCreateStates.photos` принимает два типа ввода:

### Фото

`process_item_photos()`:

- берёт самый большой размер фото из `message.photo[-1]`;
- сохраняет `file_id` в список `photos`;
- ограничивает количество фото через `ADMIN_MAX_PHOTOS`;
- просит отправить ещё фото или нажать «✅ Готово».

### Готово

`photos_done()` по тексту `✅ Готово` переводит к preview. В текущем flow фото не являются обязательными, но если они есть — будут привязаны после создания товара.

### Неверный ввод

`photos_wrong_input()` просит отправить фото или нажать кнопку готовности.

---

## 7. Preview и публикация

`show_item_confirmation()` строит preview по draft, выбранной категории/подкатегории и количеству фото. Если есть фото, helper может отправить preview с фотографией.

`process_item_confirmation()` обрабатывает callback `ADMIN_PUBLISH_ITEM_CB`.

Алгоритм:

1. достаёт draft и контекст из FSM;
2. валидирует данные через Pydantic `ItemCreate`;
3. создаёт товар через `item_service.create(..., created_by_admin_id=user.id)`;
4. привязывает фото через `photo_service` helper `attach_item_photos_or_warn()`;
5. очищает FSM;
6. показывает сообщение об успешном создании;
7. возвращает сотрудника в админское меню.

---

## 8. Отмена создания

`cancel_flow_to_main_menu()` обрабатывает `ADMIN_CANCEL_ITEM_CB`.

Он:

- подтверждает callback;
- очищает FSM;
- сообщает об отмене;
- возвращает сотрудника в админское меню.

Отмена до публикации не создаёт товар и не привязывает фото.

---

## 9. Модерация/статусы товара

`items_moderation.py` даёт быстрые действия над уже созданными товарами:

- список товаров по статусу;
- карточка товара;
- перевод в `ACTIVE`;
- скрытие в `HIDDEN`;
- возврат из `HIDDEN` в `ACTIVE`;
- архивирование в `ARCHIVED`.

Все переходы идут через `item_service.admin_set_status()`. Handler не должен сам менять поле `status`.

---

## 10. Редактирование товара

`update_item.py` сейчас содержит только стартовый callback `ADMIN_EDIT_ITEM_CB`:

1. загружает товар;
2. сохраняет edit-контекст в FSM через `init_edit_item_context()`;
3. показывает стартовый текст редактирования.

В файле прямо указано, что логика пока нерабочая/неполная. Поэтому документация фиксирует этот статус: полноценного edit FSM в текущем проекте ещё нет.

---

## 11. Правила разработки

1. Создание товара должно идти через `ItemCreateDraft` → `ItemCreate` → `ItemService`.
2. Не создавать ORM-модель товара напрямую из handler-а.
3. Фото привязывать только после успешного создания товара.
4. Валидацию пользовательского ввода держать в `create_item_helpers/validate.py`.
5. Status-actions товара выполнять только через `ItemService.admin_set_status()`.
6. Если реализуется редактирование, нужно добавить полноценные FSM-состояния, схемы update и документацию по каждому редактируемому полю.