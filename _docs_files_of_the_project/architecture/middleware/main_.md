# Документация по middleware проекта

Документ описывает актуальную middleware-цепочку Telegram-бота и контракты каждого middleware.

Текущий проект — aiogram-бот компании по аренде товаров. Middleware здесь решают четыре задачи:
- единообразно ловят технические ошибки;
- прокидывают сервисы в `data` для DI в handlers;
- проверяют регистрацию, бан и телефон клиента;
- ограничивают доступ к админским роутерам whitelist-ом Telegram ID.

---

## 0. Где подключаются middleware

Подключение находится в `app/middlewares_setup.py`, функция `register_middlewares(...)`.

### Фактический порядок подключения

1. `GlobalErrorMiddleware`
   - подключён глобально на `dp.message` и `dp.callback_query`;
   - стоит первым в коде подключения, чтобы оборачивать дальнейшую цепочку.

2. `ServicesMiddleware`
   - подключён глобально на `dp.message` и `dp.callback_query`;
   - кладёт сервисы и `admin_ids` в `data`.

3. `RegistrationCheckMiddleware`
   - подключён глобально на `dp.message` и `dp.callback_query`;
   - проверяет, можно ли пользователю пройти в рабочую часть бота.

4. `AdminCheckMiddleware`
   - подключён не глобально, а только на `admin_router.message` и `admin_router.callback_query`;
   - защищает админские handlers.

```text
Update
  -> GlobalErrorMiddleware
  -> ServicesMiddleware
  -> RegistrationCheckMiddleware
  -> handler обычного router

Update в admin_router
  -> GlobalErrorMiddleware
  -> ServicesMiddleware
  -> RegistrationCheckMiddleware
  -> AdminCheckMiddleware
  -> admin handler
```

### Почему порядок важен

- `GlobalErrorMiddleware` должен видеть ошибки всех следующих middleware/handlers.
- `ServicesMiddleware` должен отработать до `RegistrationCheckMiddleware`, потому что регистрационный guard использует `user_service` напрямую из своего `__init__`, но handlers дальше получают сервисы именно из `data`.
- `RegistrationCheckMiddleware` должен отработать до admin-guard, чтобы положить `user` в `data`.
- `AdminCheckMiddleware` нельзя делать глобальным, иначе обычные клиентские handlers станут недоступны.

---

## 1. `ServicesMiddleware`

Файл: `middlewares/services.py`.

### Что делает

`ServicesMiddleware` добавляет заранее собранные сервисы в `data`, чтобы aiogram мог подставлять их в параметры handler-функций.

Пример:

```python
async def handler(message: Message, item_service: ItemService, user):
    ...
```

aiogram берёт:
- `item_service` из `data["item_service"]`;
- `user` из `data["user"]`, который позже добавит `RegistrationCheckMiddleware`.

### Что кладётся в `data`

В `app/middlewares_setup.py` создаётся один экземпляр `ServicesMiddleware` с такими ключами:

- `user_service`
- `category_service`
- `item_service`
- `rental_service`
- `photo_service`
- `review_service`
- `admin_service`
- `admin_directory_service`
- `admin_rental_service`
- `support_service`
- `notification_service`
- `admin_ids`

### Важная особенность

Сейчас используется:

```python
data.update(self.services)
```

Это значит: если в `data` уже был ключ с таким же именем, он будет перезаписан.

В текущей цепочке это нормально, потому что `ServicesMiddleware` идёт до middleware, которые кладут `user`. Но если появятся новые middleware до DI-слоя, нужно помнить: `data.update(...)` перезаписывает ключи молча.

### Контракт

- Не ходит в БД.
- Не проверяет права.
- Не ловит ошибки.
- Только дополняет `data` и передаёт управление дальше.

---

## 2. `RegistrationCheckMiddleware`

Файл: `middlewares/registration_check.py`.

### Что делает

`RegistrationCheckMiddleware` — глобальный входной guard для обычной рабочей части бота.

Он:
1. Берёт Telegram ID из `event.from_user.id`.
2. Блокирует event без Telegram ID.
3. Пропускает `/start` без проверки регистрации.
4. Загружает пользователя через `UserService.get_by_telegram_id(...)`.
5. Если пользователя нет, пропускает только сообщение с контактом, чтобы регистрация могла завершиться.
6. Если пользователя нет и это не контакт — отвечает `MSG_NEED_REGISTER` и останавливает цепочку.
7. Если пользователь найден — кладёт DTO/объект пользователя в `data["user"]`.
8. Если пользователь `BANNED` и не admin из whitelist — отвечает `MSG_BANNED` и останавливает цепочку.
9. Если у пользователя нет телефона и это не контакт — отвечает `MSG_NEED_PHONE` и останавливает цепочку.
10. Если всё хорошо — вызывает следующий handler.

### Что пропускается без полного guard

#### `/start`

```text
/start -> handler
```

Это нужно, чтобы новый пользователь мог начать регистрацию.

#### Сообщение с контактом от ещё не найденного пользователя

```text
contact message -> handler
```

Это нужно, чтобы пользователь мог завершить регистрацию телефоном. Если не сделать исключение, бот не пустит пользователя к handler-у, который сохраняет контакт.

### Что кладётся в `data`

```python
data["user"] = user
```

Дальше handlers могут объявлять параметр `user`, и aiogram подставит его автоматически.

### Проверка бана

Бан берётся из `AccountStatus.BANNED`.

Особенность: админы из whitelist проходят даже если `user.account_status == BANNED`.

```text
BANNED + not admin -> deny(MSG_BANNED)
BANNED + admin     -> пропустить дальше
```

### Проверка телефона

Если `user.phone` пустой, middleware не пускает пользователя в рабочие handlers, кроме события с контактом.

Это закрепляет правило проекта: рабочая часть бота доступна только после завершения регистрации с телефоном.

### Helpers

- `_tg_user_id(event)` — достаёт `event.from_user.id`.
- `_is_start_command(event)` — `True` только для `Message` с текстом, начинающимся на `/start`.
- `_is_contact_message(event)` — `True` только для `Message` с `message.contact`.
- `_is_admin(tg_user_id)` — проверяет membership в `admin_ids`.

### Контракт остановки цепочки

Если доступ запрещён, middleware возвращает `None` и не вызывает handler.

---

## 3. `AdminCheckMiddleware`

Файл: `middlewares/admin_check.py`.

### Что делает

`AdminCheckMiddleware` защищает админские роутеры.

Сейчас критерий доступа простой:

```text
Telegram ID пользователя должен быть в admin_ids whitelist
```

Проверка не опирается на `Admin.role` и не читает таблицу `admins`. Роли/профили сотрудников существуют в доменной модели, но этот middleware пока допускает админа именно по whitelist из настроек.

### Где подключён

Только на `admin_router`:

```python
admin_router.message.middleware(admin_guard)
admin_router.callback_query.middleware(admin_guard)
```

Обычные клиентские роутеры этим guard-ом не защищаются.

### Как определяется Telegram ID

Helper `_get_tg_id(event, data)` делает два шага:

1. Основной путь — берёт `data["user"].telegram_id`, если `RegistrationCheckMiddleware` уже положил пользователя.
2. Fallback — берёт `event.from_user.id`, если `user` в `data` нет.

### Что происходит при отказе

Если Telegram ID не найден или не входит в `admin_ids`:
- пишется warning в лог;
- вызывается `deny(event, ONLY_FOR_ADMINS, alert_text="Нет доступа", show_alert=True)`;
- возвращается `None`, handler не вызывается.

### Контракт

- Не проверяет `AdminRole`.
- Не проверяет `Admin.is_active`.
- Не проверяет `Admin.account_status` напрямую.
- Работает как быстрый whitelist guard для админского раздела.

---

## 4. `GlobalErrorMiddleware`

Файл: `middlewares/global_error.py`.

### Что делает

`GlobalErrorMiddleware` — единый обработчик неожиданных технических ошибок.

Он:
1. Оборачивает вызов следующего handler/middleware в `try`.
2. Не трогает бизнес-ошибки `ServiceError`: они пробрасываются дальше и должны обрабатываться handlers.
3. Ловит остальные `Exception`.
4. Логирует stacktrace через `logger.exception(...)`.
5. Пытается отправить пользователю безопасный нейтральный ответ.
6. Если даже отправка ответа упала — логирует вторую ошибку, но не падает повторно.
7. Возвращает `None`, чтобы остановить цепочку и не пробрасывать техническую ошибку дальше.

### Ответ пользователю

- Для `Message`: `event.answer(err_for_msg)`.
- Для `CallbackQuery`: `event.answer(err_for_callback, show_alert=True)`.
- Для неизвестного типа события: ничего не отправляет.

Текст берётся из `texts/text_middleware.py`:
- `err_for_msg`;
- `err_for_callback`.

### Что не ловит как технический сбой

`ServiceError` специально пробрасывается:

```python
except ServiceError:
    raise
```

Причина: это доменные/сервисные ошибки, для которых handler может показать пользователю конкретное сообщение.

### Что ловит

Все прочие неожиданные ошибки:
- ошибки кода;
- неожиданные `RuntimeError`;
- непойманные ошибки БД/Telegram API, если они не обработаны ниже;
- любые другие `Exception`.

### Важный контракт

Middleware не пробрасывает техническое исключение дальше. Это сделано, чтобы избежать дубля логов и падения event-processing.

---

## 5. `data` как DI-контейнер

В aiogram `data` — общий словарь, через который middleware передают значения handlers.

В проекте туда кладутся:

| Ключ | Кто кладёт | Что это |
|---|---|---|
| `user_service` | `ServicesMiddleware` | сервис клиентов |
| `category_service` | `ServicesMiddleware` | сервис категорий |
| `item_service` | `ServicesMiddleware` | сервис товаров |
| `rental_service` | `ServicesMiddleware` | сервис заявок |
| `photo_service` | `ServicesMiddleware` | сервис фото |
| `review_service` | `ServicesMiddleware` | сервис отзывов |
| `admin_service` | `ServicesMiddleware` | audit-сервис админских действий |
| `admin_directory_service` | `ServicesMiddleware` | сервис сотрудников |
| `admin_rental_service` | `ServicesMiddleware` | сервис админской обработки заявок |
| `support_service` | `ServicesMiddleware` | сервис поддержки |
| `notification_service` | `ServicesMiddleware` | сервис уведомлений |
| `admin_ids` | `ServicesMiddleware` | whitelist Telegram ID админов |
| `user` | `RegistrationCheckMiddleware` | текущий зарегистрированный пользователь |

### Правило именования

Имя параметра handler-а должно совпадать с ключом в `data`.

```python
async def handler(message: Message, user, item_service: ItemService):
    ...
```

Здесь aiogram подставит `user` и `item_service` из `data`.

---

## 6. Практические правила для разработки

1. **Новые сервисы добавлять в `AppServices`, `build_services(...)` и `ServicesMiddleware`.** Иначе handler не сможет получить сервис через DI.
2. **Не класть в `data` случайные ключи с именами сервисов.** `ServicesMiddleware` сейчас использует `data.update(...)` и может перезаписать значения.
3. **Клиентские handlers должны рассчитывать, что `user` уже проверен.** После `RegistrationCheckMiddleware` пользователь зарегистрирован, не забанен и имеет телефон.
4. **Админские handlers должны висеть под `admin_router`.** Только тогда сработает `AdminCheckMiddleware`.
5. **Не ловить технические ошибки в каждом handler без необходимости.** Неожиданные ошибки централизованно ловит `GlobalErrorMiddleware`.
6. **`ServiceError` — не для глобального middleware.** Его нужно превращать в понятный UX на уровне handler-а или сервисного flow.
7. **Если меняется регистрационный flow, обязательно проверить исключения `/start` и contact-message.** Иначе новый пользователь может застрять до регистрации.