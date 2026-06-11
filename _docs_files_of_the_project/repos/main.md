# Документация по репозиториям проекта

Документ описывает актуальный слой `db/repositories`: какие ORM-сущности обслуживает каждый репозиторий, какие методы доступны, какие фильтры/сортировки используются и что возвращается наружу.

---

## Base

`BaseRepository` — базовый класс для всех репозиториев. Он закрепляет единый стиль работы с БД:
- единая фабрика `AsyncSession` через `self._session()`
- единые read-helper'ы для `select`
- безопасный `commit` с `rollback` при исключении
- переиспользуемые write-helper'ы для `create / update / delete / update statement`

### Методы:
- `__init__(session_factory)` — сохраняет фабрику async-сессий.
- `_session` — async context manager для открытия `AsyncSession`.
- `_list` — выполнить `Select` и вернуть `list[Any]` через `scalars()`.
- `_one_or_none` — выполнить `Select` и вернуть один ORM-объект или `None`.
- `_exists` — выполнить `Select` и вернуть `bool`.
- `_commit_or_rollback` — сделать `commit`; при ошибке сделать `rollback` и пробросить исключение.
- `_add_commit_refresh` — `add + commit + refresh`, возвращает созданный объект.
- `_commit_refresh` — `commit + refresh`, возвращает обновлённый объект.
- `_delete_commit` — `delete + commit`, возвращает `True`.
- `_execute_update_commit` — выполнить SQLAlchemy `update(...)`, сделать commit, вернуть `True`, если `rowcount > 0`.

### Возвращаются:
- `list[Any]`
- `Optional[Any]`
- `bool`
- ORM-объект после `refresh`

---

## Category

Репозиторий категорий и подкатегорий каталога. Поддерживает дерево через `parent_id`, активность через `is_active`, ручную сортировку через `sort_order` и технические ссылки через `slug`.

### Важные особенности:
- `_UNSET = object()` используется, чтобы отличать «поле не передали» от «поле передали как `None`». Это важно для nullable-полей `emoji`, `parent_id`, `slug`.
- Уникальность/поиск внутри родителя строится отдельно для `name` и `slug`.
- Публичные методы каталога по умолчанию часто используют `active_only=True`, чтобы скрытые категории не попадали клиентам.
- Сортировка каталога: `sort_order ASC`, затем `name ASC`, затем `id ASC`.

### Внутренние helpers:
- `_name_within_parent_condition(name, parent_id)` — условие поиска по имени внутри родителя:
  * `parent_id=None` — корневая категория;
  * `parent_id=X` — подкатегория внутри категории `X`.
- `_slug_within_parent_condition(slug, parent_id)` — аналогично, но по `slug`.

### Методы:
- `list_all(active_only=False)` — получить все категории и подкатегории. По умолчанию отдаёт и скрытые записи, удобно для админки.
- `list_roots(active_only=True)` — получить корневые категории без подкатегорий, по умолчанию только активные.
- `get_by_id(category_id)` — получить категорию или подкатегорию по ID.
- `list_subcategories(parent_id, active_only=True)` — получить подкатегории родителя, по умолчанию только активные.
- `get_by_name_within_parent(name, parent_id)` — найти категорию/подкатегорию по имени внутри родителя.
- `exists_by_name_within_parent(name, parent_id)` — проверить существование имени внутри родителя.
- `get_by_slug_within_parent(slug, parent_id)` — найти категорию/подкатегорию по slug внутри родителя.
- `exists_by_slug_within_parent(slug, parent_id)` — проверить существование slug внутри родителя.

> `create`
- Создаёт категорию или подкатегорию.
- Параметры: `name`, `emoji=None`, `parent_id=None`, `sort_order=0`, `is_active=True`, `slug=None`.
- `parent_id=None` — создать корневую категорию.
- `parent_id=X` — создать подкатегорию категории `X`.
- Дубликаты в самом репозитории не отсекаются — проверку уникальности должен делать сервис/БД.

> `update`
- Обновляет поля категории/подкатегории: `name`, `emoji`, `parent_id`, `sort_order`, `is_active`, `slug`.
- Если объект не найден — возвращает `None`.
- Если поле не передано — не трогает его.
- Для `emoji`, `parent_id`, `slug` можно явно передать `None`, потому что используется `_UNSET`.
- Если реальных изменений нет — возвращает текущий объект без commit.
- Если изменения есть — делает `commit/refresh`.

> `delete`
- Удаляет категорию или подкатегорию.
- Возвращает `True`, если удалили.
- Возвращает `False`, если запись не найдена.
- При удалении родительской категории подкатегории должны удаляться каскадом на уровне модели/БД.

### Возвращаются:
- `Category`
- `list[Category]`
- `Optional[Category]`
- `bool`
- не возвращает DTO/Pydantic

---

## Item

Репозиторий товаров каталога компании. Текущая модель уже не про пользовательские объявления владельцев, а про каталог товаров компании, который создаётся и обновляется администраторами/менеджерами.

### Важные особенности:
- `active_only=True` означает фильтр `Item.status == ItemStatus.ACTIVE`.
- Сортировка каталога: `sort_order ASC`, затем `id DESC`.
- Поиск идёт по `title`, `description`, `short_description` через `ilike`.
- `create(...)` использует `item_data.model_dump(exclude_none=True)`.
- `update(...)` использует `exclude_unset=True`, чтобы не перетирать непереданные поля.
- `updated_by_admin_id` записывается только если реально были изменения и параметр передан.

### Внутренние helpers:
- `_apply_active_filter(stmt)` — оставить только `ACTIVE`-товары.
- `_apply_catalog_order(stmt)` — стабильный порядок каталога.
- `_apply_pagination(stmt, limit, offset)` — применить пагинацию, если `limit is not None`.

### Методы:
- `list_all(active_only=True, limit=None, offset=0)` — все товары каталога, по умолчанию только опубликованные/активные.
- `get_by_id(item_id)` — получить товар по ID.
- `list_by_created_admin_id(admin_id, active_only=False)` — товары, созданные указанным администратором/менеджером.
- `list_by_updated_admin_id(admin_id, active_only=False)` — товары, последний раз обновлённые указанным администратором/менеджером.
- `list_by_category(category_id, active_only=True)` — товары категории.
- `list_by_subcategory(subcategory_id, active_only=True)` — товары подкатегории.
- `search(query, active_only=True, limit=50, offset=0)` — поиск по `title OR description OR short_description`.
- `list_by_status(status, limit, offset=0)` — товары по статусу с пагинацией для админки.
- `list_drafts(limit, offset=0)` — товары со статусом `DRAFT`.
- `set_status(item_id, new_status, updated_by_admin_id=None)` — техническое обновление статуса товара.

> `create`
- Создаёт товар каталога компании.
- Принимает `ItemCreate`.
- Дополнительно принимает `created_by_admin_id` и `status`.
- Статус по умолчанию: `ItemStatus.DRAFT`.
- После создания делает `add + commit + refresh`.

> `update`
- Обновляет поля товара по `ItemUpdate`.
- Если товар не найден — возвращает `None`.
- Если patch пустой — возвращает текущий ORM без commit.
- Если значения совпадают с текущими — возвращает текущий ORM без commit.
- Если изменения есть — применяет изменения, при необходимости пишет `updated_by_admin_id`, делает `commit/refresh`.

> `set_status`
- Получает объект по ID.
- Если товара нет — возвращает `None`.
- Пишет новый `status`.
- Ставит `moderated_at = datetime.now(timezone.utc)`.
- Если передан `updated_by_admin_id`, записывает его.
- Делает `commit/refresh`.
- Бизнес-проверки переходов статусов должны выполняться сервисом.

> `delete`
- Удаляет товар каталога.
- Возвращает `True`, если удалили.
- Возвращает `False`, если запись не найдена.

### Возвращаются:
- `Item`
- `list[Item]`
- `Optional[Item]`
- `bool`
- не возвращает DTO/Pydantic

---

## Photo

Репозиторий фотографий товаров каталога. Отвечает за хранение фото, главную фотографию товара и порядок фотографий внутри карточки.

### Важные особенности:
- Фото выбираются внутри товара по `item_id`.
- Порядок фото: `sort_order ASC`, затем `id ASC`.
- Главная фотография определяется флагом `is_main`.
- Методы перестановки работают только внутри одного `item_id` и проверяют принадлежность `photo_id` товару.

### Внутренние helpers:
- `_apply_item_filter(stmt, item_id)` — фильтр по товару.
- `_apply_order(stmt)` — стабильная сортировка фото.
- `_apply_main_filter(stmt)` — оставить только главные фото.
- `_photos_in_order(session, item_id)` — получить фото товара в текущем порядке.

### Методы:
- `get_by_id(photo_id)` — получить фото по ID.
- `list_by_item_id(item_id)` — получить все фото товара.
- `get_main_by_item_id(item_id)` — получить главную фотографию товара или `None`.
- `count_by_item(item_id)` — количество фотографий товара.

> `create`
- Создаёт фотографию товара.
- Параметры: `item_id`, `telegram_file_id=None`, `url=None`, `order=0`, `is_main=False`.
- Поле порядка в модели: `sort_order=order`.

> `update`
- Обновляет `telegram_file_id`, `url`, `sort_order`, `is_main`.
- Если фото не найдено — возвращает `None`.
- Если параметр равен `None`, поле не меняется. Поэтому этим методом нельзя явно обнулить `telegram_file_id/url`.
- Если изменений нет — возвращает текущий объект без commit.
- Если изменения есть — делает `commit/refresh`.

> `delete`
- Удаляет фото по ID.
- Возвращает `True`, если удалено.
- Возвращает `False`, если фото не найдено.

> `reorder`
- Уплотняет `sort_order` фотографий товара до `0..N`.
- Возвращает количество обработанных фото.
- Если фото нет — возвращает `0`.

> `set_main`
- Делает одну фотографию главной внутри товара.
- Сначала проверяет, что `photo_id` принадлежит `item_id`.
- Для выбранного фото ставит `is_main=True`, для остальных — `False`.
- Возвращает `True`, если успешно; `False`, если фото не принадлежит товару.

> `swap_with_neighbor`
- Меняет фото местами с соседним внутри товара.
- `direction="up"` — поднять выше.
- `direction="down"` — опустить ниже.
- Возвращает `False`, если фото не найдено в товаре или уже находится на границе.
- После swap заново записывает плотный `sort_order`.

> `set_order`
- Перемещает фото на конкретную позицию `new_order`.
- Проверяет принадлежность фото товару и валидность позиции.
- Если фото уже на нужной позиции — возвращает `True` без commit.
- После перестановки уплотняет `sort_order`.

### Возвращаются:
- `Photo`
- `list[Photo]`
- `Optional[Photo]`
- `int`
- `bool`
- не возвращает DTO/Pydantic

---

## User

Репозиторий клиентов. Отвечает за регистрацию/поиск клиента, выборку по статусу аккаунта и обновление клиентских/админских полей.

### Важные особенности:
- Сортировка пользователей стабильная: `id ASC`.
- Поддерживается пагинация `limit/offset`.
- `create(...)` сейчас использует `user_data.model_dump()` без `exclude_none=True`.
- `delete(...)` физически удаляет пользователя. Для боевого сценария лучше рассматривать бан/деактивацию через `account_status`, а не физическое удаление.
- Ранее удалён отдельный `update_rating`; рейтинг пользователя не обновляется этим репозиторием.

### Внутренние helpers:
- `_apply_account_status_filter(stmt, status)` — фильтр по статусу аккаунта.
- `_apply_id_order(stmt)` — сортировка по `User.id.asc()`.
- `_apply_pagination(stmt, limit, offset)` — применить пагинацию при наличии `limit`.

### Методы:
- `list_all(limit=None, offset=0)` — получить всех клиентов по ID по возрастанию.
- `list_by_acc_status(status, limit=None, offset=0)` — получить клиентов с указанным `AccountStatus`.
- `get_by_id(user_id)` — найти клиента по ID.
- `get_by_telegram_id(telegram_id)` — найти клиента по Telegram ID.
- `exists_by_telegram_id(telegram_id)` — проверить существование клиента по Telegram ID.

> `create`
- Создаёт клиента из `UserCreate`.
- Делает `add + commit + refresh`.

> `update`
- Принимает `UserUpdate | UserAdminUpdate`.
- Если клиент не найден — возвращает `None`.
- Если patch пустой — возвращает текущий объект без commit.
- Если значения не изменились — возвращает текущий объект без commit.
- Если изменения есть — делает `commit/refresh`.

> `delete`
- Физически удаляет клиента.
- Возвращает `True`, если удалён.
- Возвращает `False`, если не найден.

### Возвращаются:
- `User`
- `list[User]`
- `Optional[User]`
- `bool`
- не возвращает DTO/Pydantic

---

## Admin

Репозиторий администраторов и менеджеров компании. Поддерживает выборки по роли, статусу аккаунта и активности доступа к админке.

### Важные особенности:
- Стабильная сортировка сотрудников: `id ASC`.
- `active_only=True` фильтрует по `Admin.is_active.is_(True)`.
- Статус аккаунта берётся из `AccountStatus`.
- Роль сотрудника берётся из `AdminRole`.

### Внутренние helpers:
- `_apply_id_order(stmt)` — сортировка по `Admin.id.asc()`.
- `_apply_pagination(stmt, limit, offset)` — пагинация при наличии `limit`.
- `_apply_role_filter(stmt, role)` — фильтр по роли.
- `_apply_account_status_filter(stmt, status)` — фильтр по статусу аккаунта.
- `_apply_active_filter(stmt)` — фильтр по включённому админ-доступу.

### Методы:
- `list_all(active_only=False, limit=None, offset=0)` — список администраторов/менеджеров.
- `list_by_role(role, active_only=False, limit=None, offset=0)` — сотрудники с указанной ролью.
- `list_by_account_status(status, limit=None, offset=0)` — сотрудники с указанным статусом аккаунта.
- `get_by_id(admin_id)` — найти сотрудника по ID.
- `get_by_telegram_id(telegram_id)` — найти сотрудника по Telegram ID.
- `exists_by_telegram_id(telegram_id)` — проверить существование сотрудника по Telegram ID.

> `create`
- Создаёт администратора/менеджера из `AdminCreate`.
- Использует `admin_data.model_dump()`.
- Делает `add + commit + refresh`.

> `update`
- Обновляет данные сотрудника из `AdminUpdate`.
- Если сотрудник не найден — возвращает `None`.
- Если patch пустой — возвращает текущий объект без commit.
- Если значения не изменились — возвращает текущий объект без commit.
- Если изменения есть — делает `commit/refresh`.

> `delete`
- Физически удаляет администратора/менеджера.
- Возвращает `True`, если удалён.
- Возвращает `False`, если не найден.

### Возвращаются:
- `Admin`
- `list[Admin]`
- `Optional[Admin]`
- `bool`
- не возвращает DTO/Pydantic

---

## AdminAction

Репозиторий журнала действий администратора. Хранит audit-записи: кто (`admin_id/admin_tg_id`), что сделал (`action_type`), над какой сущностью (`entity_type/entity_id`) и с каким дополнительным payload/note.

### Важные особенности:
- Сортировка audit-журнала: `created_at DESC`, затем `id DESC`.
- `entity_id` при фильтрации приводится к строке: `str(entity_id)`.
- Пагинация поддерживается почти во всех list-методах.
- Репозиторий только создаёт и читает audit-записи; update/delete методов нет.

### Внутренние helpers:
- `_apply_recent_order(stmt)` — новые audit-записи первыми.
- `_apply_pagination(stmt, limit, offset)` — пагинация при наличии `limit`.
- `_apply_admin_id_filter(stmt, admin_id)` — фильтр по внутреннему ID администратора.
- `_apply_admin_tg_id_filter(stmt, admin_tg_id)` — фильтр по Telegram ID администратора.
- `_apply_entity_filter(stmt, entity_type, entity_id)` — фильтр по сущности.
- `_apply_action_type_filter(stmt, action_type)` — фильтр по типу действия.

### Методы:
- `list_recent(limit=None, offset=0)` — последние audit-записи.
- `list_by_admin_id(admin_id, limit=None, offset=0)` — audit-записи внутреннего администратора.
- `list_by_admin_tg_id(admin_tg_id, limit=None, offset=0)` — audit-записи администратора по Telegram ID.
- `list_by_entity(entity_type, entity_id, limit=None, offset=0)` — audit-записи по конкретной сущности.
- `list_by_action_type(action_type, limit=None, offset=0)` — audit-записи указанного типа.
- `get_by_id(action_id)` — найти audit-запись по ID.

> `create`
- Создаёт запись о действии администратора.
- Обязательные поля: `admin_tg_id`, `action_type`, `entity_type`, `entity_id`.
- Дополнительные поля: `admin_id=None`, `note=None`, `payload=None`.
- Делает `add + commit + refresh`.

### Возвращаются:
- `AdminAction`
- `list[AdminAction]`
- `Optional[AdminAction]`
- не возвращает DTO/Pydantic

---

## Rental

Репозиторий заявок клиентов на аренду товаров компании. Отвечает за чтение заявок, фильтрацию по товару/клиенту/менеджеру/статусу, создание/обновление, атомарные переходы статусов и проверку открытых заявок по товару.

### Важные особенности:
- Сортировка заявок: `created_at DESC`, затем `id DESC`.
- Открытые заявки определяются через `open_statuses()` из `status.rental_status`.
- Для админских экранов есть методы с заранее подгруженными связями через `selectinload`.
- `_OPEN_RENTAL_LOOKUP_LIMIT = 10` ограничивает количество последних открытых заявок по товару.
- Атомарные переходы статусов выполняются через `update(...).where(...expected_status...)` и возвращают `bool`.

### Внутренние helpers:
- `_apply_recent_order(stmt)` — новые заявки первыми.
- `_apply_pagination(stmt, limit, offset)` — пагинация при наличии `limit`.
- `_apply_status_filter(stmt, status)` — фильтр по статусу.
- `_apply_open_status_filter(stmt)` — фильтр по открытым статусам.
- `_apply_item_filter(stmt, item_id)` — фильтр по товару.
- `_apply_user_filter(stmt, user_id)` — фильтр по клиенту.
- `_apply_assigned_admin_filter(stmt, admin_id)` — фильтр по назначенному менеджеру.
- `_with_details(stmt)` — подгрузить `Rental.item`, `Rental.user`, `Rental.assigned_admin`.

### Методы:
- `list_all(limit=None, offset=0)` — все заявки клиентов.
- `get_by_id(rental_id)` — найти заявку по ID.
- `list_by_item_id(item_id, limit=None, offset=0)` — заявки по товару.
- `list_by_user_id(user_id, limit=None, offset=0)` — заявки клиента.
- `list_by_assigned_admin_id(admin_id, limit=None, offset=0)` — заявки, назначенные менеджеру.
- `list_by_status(status, limit=None, offset=0)` — заявки по статусу.
- `get_details_by_id(rental_id)` — заявка с заранее подгруженными товаром, клиентом и менеджером.
- `list_recent_open_by_item_id(item_id)` — последние открытые заявки по товару, максимум 10.
- `list_recent(limit, offset=0)` — последние заявки для админки.
- `list_recent_with_details_for_admins(limit, offset)` — последние заявки для админки с подгруженными связями.

> `create`
- Создаёт заявку из `RentalCreate`.
- Использует `rental_data.model_dump()`.
- Делает `add + commit + refresh`.

> `update`
- Обновляет заявку из `RentalUpdate`.
- Если заявка не найдена — возвращает `None`.
- Если patch пустой — возвращает текущий объект без commit.
- Если значения не изменились — возвращает текущий объект без commit.
- Если изменения есть — делает `commit/refresh`.

> `delete`
- Удаляет заявку по ID.
- Возвращает `True`, если удалена.
- Возвращает `False`, если не найдена.

> `try_update_status`
- Атомарно меняет статус заявки, если текущий статус равен `expected_status`.
- Параметры: `rental_id`, `new_status`, `expected_status`.
- Возвращает `True`, если строка обновлена; `False`, если условие не совпало.

> `try_update_status_if_user`
- Атомарно меняет статус заявки, если заявка принадлежит `user_id` и текущий статус равен `expected_status`.
- Используется для пользовательских переходов, где важно проверить владельца действия.

> `has_open_rentals_for_item`
- Проверяет, есть ли у товара открытые заявки.
- Используется сервисом товаров при модерации/изменении доступности.

### Возвращаются:
- `Rental`
- `list[Rental]`
- `Optional[Rental]`
- `bool`
- не возвращает DTO/Pydantic

---

## Review

Репозиторий отзывов клиентов о товарах, заявках и сервисе компании. Поддерживает клиентское создание/редактирование отзыва, админскую модерацию, выборки по связанным сущностям и расчёт статистики по товару.

### Важные особенности:
- Сортировка отзывов: `created_at DESC`, затем `id DESC`.
- Для отзывов по товару есть флаг `published_only`, который оставляет только `ReviewStatus.PUBLISHED`.
- `exists_for_rental(...)` проверяет, оставлял ли конкретный клиент отзыв по конкретной заявке.
- `get_stats_for_item(...)` по умолчанию считает статистику только по опубликованным отзывам.

### Внутренние helpers:
- `_apply_recent_order(stmt)` — новые отзывы первыми.
- `_apply_pagination(stmt, limit, offset)` — пагинация при наличии `limit`.
- `_apply_rental_filter(stmt, rental_id)` — фильтр по заявке.
- `_apply_user_filter(stmt, user_id)` — фильтр по клиенту.
- `_apply_item_filter(stmt, item_id)` — фильтр по товару.
- `_apply_status_filter(stmt, status)` — фильтр по статусу модерации.

### Методы:
- `get_by_id(review_id)` — получить отзыв по ID.
- `list_all(limit=None, offset=0)` — все отзывы.
- `list_by_rental_id(rental_id, limit=None, offset=0)` — отзывы по заявке.
- `list_by_user_id(user_id, limit=None, offset=0)` — отзывы, оставленные клиентом.
- `list_by_item_id(item_id, published_only=False, limit=None, offset=0)` — отзывы по товару.
- `list_by_status(status, limit=None, offset=0)` — отзывы с указанным статусом модерации.
- `exists_for_rental(rental_id, user_id)` — проверить наличие отзыва клиента по заявке.

> `create`
- Создаёт отзыв из `ReviewCreateInternal`.
- Использует `review_data.model_dump()`.
- Делает `add + commit + refresh`.

> `update`
- Клиентское обновление оценки или текста отзыва через `ReviewUpdate`.
- Если отзыв не найден — возвращает `None`.
- Если patch пустой — возвращает текущий объект без commit.
- Если значения не изменились — возвращает текущий объект без commit.
- Если изменения есть — делает `commit/refresh`.

> `delete`
- Удаляет отзыв.
- Возвращает `True`, если удалён.
- Возвращает `False`, если не найден.

> `admin_update`
- Админское обновление статуса модерации или внутренней заметки через `ReviewAdminUpdate`.
- Поведение такое же: `None`, если не найден; без commit, если нет изменений; `commit/refresh`, если изменения есть.

> `set_status`
- Устанавливает статус модерации отзыва.
- Может дополнительно записать `admin_note`, если он передан.
- Если статус и заметка не изменились — возвращает текущий объект без commit.

> `get_stats_for_item`
- Возвращает `(avg_rating, count)` по товару.
- Параметр `status` по умолчанию `ReviewStatus.PUBLISHED`.
- Если `status=None`, статистика считается по всем отзывам товара.
- Средний рейтинг возвращается как `Decimal`; если отзывов нет, используется `Decimal("0.00")`.

### Возвращаются:
- `Review`
- `list[Review]`
- `Optional[Review]`
- `tuple[Decimal, int]`
- `bool`
- не возвращает DTO/Pydantic

---

## SupportTicket

Репозиторий обращений клиентов в поддержку. Поддерживает открытые/закрытые тикеты, выборки по клиенту/товару/заявке/админу, закрытие тикета и отметку последнего ответа администратора.

### Важные особенности:
- Сортировка обращений: `created_at DESC`, затем `id DESC`.
- Открытый тикет — статус `SupportTicketStatus.OPEN`.
- Закрытие тикета сделано атомарным `update`: закрыть можно только открытый тикет.
- `touch_admin_reply(...)` обновляет `admin_last_reply_at`, чтобы видеть последнюю активность админа и сортировать/контролировать обращения.

### Внутренние helpers:
- `_apply_recent_order(stmt)` — новые обращения первыми.
- `_apply_pagination(stmt, limit, offset)` — пагинация при наличии `limit`.
- `_apply_id_filter(stmt, ticket_id)` — фильтр по ID обращения.
- `_apply_status_filter(stmt, status)` — фильтр по статусу.
- `_apply_user_filter(stmt, user_id)` — фильтр по клиенту.
- `_apply_item_filter(stmt, item_id)` — фильтр по товару.
- `_apply_rental_filter(stmt, rental_id)` — фильтр по заявке на аренду.
- `_apply_closed_by_admin_filter(stmt, admin_id)` — фильтр по админу/менеджеру, который закрыл обращение.

### Методы:
- `get_by_id(ticket_id)` — получить обращение по ID.
- `get_open_by_user_id(user_id, offset=0)` — получить последнее открытое обращение клиента.
- `list_all(limit=None, offset=0)` — все обращения клиентов в поддержку.
- `list_open(limit=None, offset=0)` — открытые обращения.
- `list_by_status(status, limit=None, offset=0)` — обращения с указанным статусом.
- `list_by_user_id(user_id, limit=None, offset=0)` — обращения клиента.
- `list_by_item_id(item_id, limit=None, offset=0)` — обращения по товару.
- `list_by_rental_id(rental_id, limit=None, offset=0)` — обращения по заявке на аренду.
- `list_by_closed_by_admin_id(admin_id, limit=None, offset=0)` — обращения, закрытые указанным администратором/менеджером.
- `count_open_by_user_id(user_id)` — количество открытых обращений клиента.

> `close`
- Атомарно закрывает открытое обращение.
- Условия: `id == ticket_id` и `status == OPEN`.
- Записывает:
  * `status = CLOSED`;
  * `closed_at = datetime.now(timezone.utc)`;
  * `closed_by_admin_id`.
- Возвращает `True`, если строка обновлена; `False`, если тикет не найден или уже не открыт.

> `touch_admin_reply`
- Обновляет `admin_last_reply_at = datetime.now(timezone.utc)`.
- Возвращает `True`, если строка обновлена.

> `create`
- Создаёт обращение из `SupportTicketCreateInternal`.
- Использует `ticket_data.model_dump()`.
- Делает `add + commit + refresh`.

> `update`
- Админское обновление обращения через `SupportTicketAdminUpdate`.
- Если обращение не найдено — возвращает `None`.
- Если patch пустой — возвращает текущий объект без commit.
- Если значения не изменились — возвращает текущий объект без commit.
- Если изменения есть — делает `commit/refresh`.

> `delete`
- Удаляет обращение по ID.
- Возвращает `True`, если удалено.
- Возвращает `False`, если не найдено.

### Возвращаются:
- `SupportTicket`
- `list[SupportTicket]`
- `Optional[SupportTicket]`
- `int`
- `bool`
- не возвращает DTO/Pydantic

---

## Общие правила репозиториев

### Что репозитории делают:
- строят SQLAlchemy-запросы;
- возвращают ORM-модели;
- делают простые CRUD-операции;
- применяют технические фильтры, сортировку, пагинацию;
- делают безопасный `commit/rollback` через `BaseRepository`.

### Что репозитории НЕ должны делать:
- не возвращать DTO/Pydantic наружу;
- не выполнять бизнес-валидации переходов статусов;
- не формировать тексты/клавиатуры для Telegram;
- не решать UI-логику;
- не скрывать сложные бизнес-правила внутри SQL-методов.

### Общий update-паттерн:
```
obj = await s.get(Model, obj_id)
if not obj:
    return None

data = update_data.model_dump(exclude_unset=True)
if not data:
    return obj

changed = False
for field_name, value in data.items():
    if getattr(obj, field_name) != value:
        setattr(obj, field_name, value)
        changed = True

if not changed:
    return obj

return await self._commit_refresh(s, obj)
```

### Общий delete-паттерн:
```
obj = await s.get(Model, obj_id)
if not obj:
    return False

return await self._delete_commit(s, obj)
```

### Общий pagination-паттерн:
```
if limit is not None:
    stmt = stmt.limit(limit).offset(offset)
```

### Общая договорённость по возвратам:
- `list[...]` — для выборок;
- `Optional[Model]` — для `get/update/set_status`, когда объект может не существовать;
- `bool` — для `exists/delete/atomic update`;
- `int` — для счётчиков;
- конкретный ORM-объект — для успешного `create`.

### Нужно фиксить:
[типизация довольно широкая: Any, Optional[Any], list[Any]]()

`create / update / delete` - либо так `obj: Any)` -> `Any:`

Нужно контролировать:
- Типизация базовых helper'ов пока широкая (`Any`, `Optional[Any]`). Это нормально для базового класса, 
но в конкретных репозиториях наружу должны возвращаться конкретные ORM-типы.

