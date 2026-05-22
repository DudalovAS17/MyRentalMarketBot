# Registration check

### _[Что делает]()_

1) Перехватывает каждый `update` до вызова твоего хендлера.
[Middleware работает как фильтр: всё сообщение сначала проходит через него]()

2) Определяет `Telegram ID` пользователя (если его нет → пропускает `update` дальше)

3) Пропускает команду `/start` без проверок. Это нужно, чтобы незарегистрированный 
пользователь мог запустить регистрацию

4) Проверяет, [существует ли пользователь в БД]()
5) Проверяет: [заблокирован ли пользователь]()
6) Проверяет: [указан ли телефон]() (в хендлеры бот пускает только пользователей с завершённой регистрацией)

7) Если всё хорошо — кладёт `user` в `data`
8) Передаёт управление хендлеру

```
👉 Middleware гарантирует, что в хендлер попадут только полностью зарегистрированные и 
не заблокированные пользователи, а новый пользователь может пройти только /start → регистрацию.
```

### _✅ Всё хорошо → добавляем пользователя в data_

Middleware кладёт значения в `data` (обычный dict). Когда вызывается хендлер, 
aiogram смотрит на имена параметров функции и пытается найти в data ключи с такими же именами.

aiogram делает примерно так (упрощённо):
- видит параметр `item_service` → ищет `data["item_service"]`
- видит параметр `user` → ищет `data["user"]`
- видит параметр `callback` → это сам `event`

Поэтому у тебя user подставляется автоматически (DI — это Dependency Injection, внедрение зависимостей)

✅ Вывод: имя параметра должно совпадать с ключом в `data`

Но помни! `data` — общий мешок, в который пишут разные `middleware`, конфликтов избегай

### _[Что внутри]()_

- `class RegistrationCheckMiddleware`
    * `__init__`
        - skip_commands: `tuple[str, ...] = ("/start", "/register")`
        - если `self.skip_commands = skip_commands` - команды, которые пропускаются без проверки
    * `__call__` - Основная точка входа в middleware
        - [handler]() - следующий обработчик в цепочке (следующий middleware или уже хендлер)
        - [data]() - DI-контейнер (в него можно докладывать переменные, которые затем -> в хендлер 
        как параметры - user, user_service, и т.д)

`deny()` - цель: “остановить цепочку и объяснить пользователю почему”

- `helpers`
    * `_tg_user_id`
    * `_is_start`
    * `_is_contact_message`

---

# Admin check

### _[Что делает]()_

Проверяет права администратора ([“пользователь — админ”]())
* Ожидает, что `RegistrationCheckMiddleware` уже положил `user` в `data["user"]`.

```
Сейчас критерий допуска простой:
`Telegram ID` пользователя должен входить в `self._admin_ids`.
```

### _[Что внутри]()_

- `class AdminCheckMiddleware`
    * `__init__`
    * `__call__`

- `helpers`
    * `_get_tg_id` - Проверить, входит ли Telegram ID пользователя в whitelist администраторов
        - Основной путь: user уже загружен `RegistrationCheckMiddleware`
            * `print("user from data =", data.get("user"))`
        - Иначе: берём из `update` (на случай, если порядок `middleware` поменяли)
            * `print("event.from_user.id =", event.from_user.id)`

---

# Admin check - Пока не актуальный??: не понимаю что и зачем

### _[Что делает]()_

`Aiogram` смотрит на аргументы твоего хендлера, например:
- `async def rent_button_handler(message: Message, category_service: CategoryService)` -
видит `category_service` и подставляет его из `data`.

`ServicesMiddleware` кладёт все твои сервисы в `data`. 
`Aiogram` сам «инжектит» их в аргументы хендлеров.

### _[Что внутри]()_

- `class ServicesMiddleware`
    * `__init__`
        - сюда кладём все сервисы при инициализации
    * `__call__`
        - добавляем сервисы в `data`, чтобы aiogram мог подставить их в хендлеры
        - Теперь `data` = `{"event_from_user": User(...), "state": FSMContext(...),
      "user_service": <UserService>, "category_service": <CategoryService>}`
    
    * В `__call__` сейчас `data.update(self.services)` (молча перезаписывает всё, если ключ уже существует), 
      но мб лучше так:
        ```
        for key, value in self.services.items():
            data.setdefault(key, value)
        ```
      Тогда логика такая:
         - если ключа ещё нет — положить сервис
         - если ключ уже есть — не затирать его

---

# Global error Middleware - актуальный???

[_Единый обработчик технических ошибок (глобальный): лог + безопасный ответ пользователю_
]()
### _[Что делает]()_

Каноничный Global Error Middleware

- Централизованный перехват только неожиданных/технических ошибок
- Stacktrace логируется один раз (`exc_info=True` / `logger.exception`)
- Пользователю отправляем нейтральный ответ:
       - `Message -> answer()`
       - `CallbackQuery -> answer(show_alert=True)`
- business errors (ServiceError) тут НЕ ловим (их ловят handlers) - НЕ содержит бизнес-логики

- Исключение НЕ пробрасываем дальше (иначе будет дубль логов / падение) - ?

### _[Что внутри]()_
- `class GlobalErrorMiddleware`
    * `__call__`
        - [Бизнес-ошибки]() не трогаем: они должны обрабатываться в `handlers`.
        - [Технические ошибки](): логируем один раз + нейтральный UX
            - Техническая ошибка -> лог со stacktrace `logger.error("Глобальная техническая ошибка: %s", exc, exc_info=True)`
              (как я понял exception = `error` + `exc_info=True` - компактней), поэтому:
              `logger.exception("Unhandled техническая ошибка: %s", exc)`
            - ответ пользователю (не раскрываем детали)


### _[Какие ошибки ловим/не ловим]()_

[1) SQLAlchemyError - Ловим тут!]()
```
except SQLAlchemyError as e:
    logger.error(" [Start] Ошибка БД при регистрации %s: %s", telegram_id, e)
    await message.answer(
        "❌ Произошла ошибка при подключении к базе данных. Попробуйте позже."
    )
    return
```
Это уже:
- ошибки БД
- инфраструктура
- технический сбой
- не бизнес-логика

[2) IntegrityError - НЕ ловим тут!]()
```
except IntegrityError:
    await message.answer("⚠️ Вы уже зарегистрированы. Используйте /start для входа в меню.")
    return
```
Обычно это значит:
- нарушение unique constraint
- у вас уже есть пользователь с таким telegram_id

Это ожидаемый сценарий гонки/повторного входа:
- юзер уже существует
- повторно вызвали регистрацию
- БД защитила от дубля
    
[3) Exception - Ловим тут!]()
```
except Exception as e:
    logger.exception("Неожиданная ошибка при регистрации %s", telegram_id)
    # logger.error(f"Ошибка при регистрации пользователя {telegram_id}: {e}", exc_info=True)
    await message.answer("⚠️ Произошла внутренняя ошибка. Попробуйте позже.")
    return
```
Что это значит: это catch-all:
- любые неожиданные ошибки
- программные баги
- неожиданные падения
    
[4) RuntimeError - Ловим тут!]()

[5) TelegramAPIError - ?]()
```
except TelegramAPIError as e:
    logger.error(f"[Start] Ошибка Telegram API: {e}")
    return await message.answer("⚠️ Ошибка при связи с Telegram. Повторите позже.")
```
Это ошибки при обращении к Telegram API, например:
- сообщение нельзя отправить
- сообщение нельзя отредактировать
- чат недоступен
- объект сообщения уже удалён
    