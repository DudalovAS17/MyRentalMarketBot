# Auth — регистрация, профиль, настройки и приватность

Раздел описывает актуальные auth/profile handlers проекта. В текущем боте пользователь — клиент компании по аренде товаров. Auth-слой отвечает за завершение регистрации через Telegram contact, просмотр профиля, редактирование контактных данных и информационные настройки.

---

## 1. Карта файлов

| Файл                            | Назначение                                                                                 |
|---------------------------------|--------------------------------------------------------------------------------------------|
| `handlers/auth/router.py`       | Создаёт общий `auth_router`.                                                               |
| `handlers/auth/__init__.py`     | Импортирует модули auth-раздела, чтобы их обработчики зарегистрировались на общем роутере. |
| `handlers/auth/complete_reg.py` | Завершение регистрации по Telegram contact.                                                |
| `handlers/auth/profile.py`      | Просмотр профиля, статистики и достижений.                                                 |
| `handlers/auth/edit_profile.py` | FSM редактирования имени, email и телефона.                                                |
| `handlers/auth/settings.py`     | Экран настроек профиля и уведомлений.                                                      |
| `handlers/auth/privacy.py`      | Приватность и политика обработки данных.                                                   |
| `handlers/auth/helpers_auth/*`  | Клавиатуры, тексты и валидация auth/profile flow.                                          |
| `handlers/auth/trash.py`        | Старый/неподключённый код, не является частью актуального aiogram flow.                    |

---

## 2. Роутер и подключение

`auth_router = Router(name="auth")` находится в `handlers/auth/router.py`. Модули `complete_reg`, `profile`, `settings`, `edit_profile`, `privacy` импортируются в `handlers/auth/__init__.py`, поэтому все декораторы навешиваются на один роутер.

В `app/routers.py` auth-роутер подключается после каталога и аренды, но до поиска, админки, поддержки и базового catch-all.

---

## 3. Завершение регистрации: `complete_reg.py`

`complete_registration_with_contact()` слушает любое сообщение с `F.contact`.

Алгоритм:

1. проверяет, что контакт принадлежит отправителю (`is_own_contact(contact, tg_user)`);
2. если пользователь ещё не найден в БД — запускает `start_registration()`;
3. обновляет `phone` через `user_service.update(user.id, UserUpdate(phone=...))`;
4. повторно загружает пользователя с `strict=True`;
5. проверяет `can_use_bot(updated_user.account_status)`;
6. при успехе сообщает о завершении регистрации и показывает главное меню.

Важно: контакт, отправленный текстом, не принимается. Пользователь должен нажать Telegram-кнопку «Поделиться контактом».

---

## 4. Профиль: `profile.py`

| Вход                       | Обработчик            | Поведение                             |
|----------------------------|-----------------------|---------------------------------------|
| текст `👤 Профиль`         | `profile()`           | Показывает карточку профиля.          |
| callback `back_to_profile` | `profile()`           | Возвращает к карточке профиля.        |
| callback `profile_stats`   | `show_statistics()`   | Показывает заглушку/экран статистики. |
| callback `achievements`    | `show_achievements()` | Показывает достижения клиента.        |

Карточка профиля строится через `build_profile_text(user)`, кнопки — через auth keyboards.

---

## 5. Настройки: `settings.py`

Настройки профиля открываются callback-кнопками:

- `profile_settings`;
- `back_to_profile_settings`.

`show_settings()` отдаёт общий экран настроек.

`show_notification_settings()` показывает экран уведомлений. В текущем коде это UI-экран, а не полноценное изменение настройки в БД: переключение уведомлений не реализовано в актуальном aiogram flow.

---

## 6. Приватность: `privacy.py`

| Callback              | Обработчик                | Назначение                       |
|-----------------------|---------------------------|----------------------------------|
| `settings_privacy`    | `show_privacy_settings()` | Экран настроек приватности.      |
| `show_privacy_policy` | `send_privacy_policy()`   | Текст политики обработки данных. |

Тексты и клавиатуры берутся из `helpers_auth/texts.py` и `helpers_auth/keyboards.py`.

---

## 7. Редактирование профиля: `edit_profile.py`

### Экран редактирования

`show_edit_profile_settings()` открывается callback `SEP` и показывает подменю:

- изменить имя;
- изменить email;
- изменить телефон.

### FSM: изменение имени

1. `ask_new_name()` по callback `EPF_NAME` ставит `ProfileEditStates.waiting_for_name`.
2. `process_edit_name()` принимает текст.
3. Значение валидируется через `validate_profile_name()`.
4. Сохраняется через `user_service.update(..., UserUpdate(full_name=...))`.
5. FSM очищается.

Особенность текущей реализации: новое имя записывается в `full_name`, составленный из `user.first_name` и введённого значения.

### FSM: изменение email

1. `ask_new_email()` по callback `EPF_EMAIL` ставит `ProfileEditStates.waiting_for_email`.
2. `process_edit_email()` принимает текст.
3. Значение валидируется через `validate_profile_email()`.
4. Сохраняется через `UserUpdate(email=new_email)`.
5. FSM очищается.

### FSM: изменение телефона

1. `request_phone_number_change()` по callback `EPF_PHONE` ставит `ProfileEditStates.waiting_for_phone`.
2. Пользователю отправляется reply-кнопка для контакта.
3. `process_phone_number()` принимает только `F.contact`.
4. Проверяет собственный контакт через `is_own_contact()`.
5. Сохраняет `UserUpdate(phone=phone_number)`.
6. FSM очищается.

Если в состоянии ожидания телефона приходит не contact, `process_invalid_phone_input()` повторно просит отправить номер через кнопку.

---

## 8. Helpers

### `helpers_auth/keyboards.py`

Содержит клавиатуры:

- возврат в профиль;
- меню редактирования профиля;
- кнопка отправки контакта;
- настройки приватности;
- политика приватности;
- настройки профиля;
- экран уведомлений.

### `helpers_auth/texts.py`

Формирует тексты профиля, статистики, достижений, prompts редактирования и политики приватности.

### `helpers_auth/validation.py`

Проверяет:

- email;
- имя профиля;
- принадлежность contact текущему Telegram-пользователю.

---

## 9. Правила разработки

1. Любой ввод профиля должен идти через FSM-состояние из `states/user.py`.
2. Не доверять телефону, введённому текстом: только Telegram contact.
3. Не создавать нового пользователя в profile/edit flow — создание допускается только через регистрацию.
4. Не смешивать настройки UI с реальными persisted-настройками: если добавляется переключатель, нужна схема/поле/сервисный метод.
5. `auth/trash.py` не использовать как источник актуальной логики.