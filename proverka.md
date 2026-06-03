# CHECK_MODEL_SCHEMA_CONTRACT_PROMPT

Проверь связку DB Models ↔ Schemas / DTO.

## Задача

Найти несоответствия между SQLAlchemy-моделями и Pydantic-схемами.

Ничего не редактируй без отдельного запроса.  
Сначала сделай анализ.

---

## 1. Соответствие полей

Проверь:

- есть ли в schemas поля, которых уже нет в DB-моделях;
- есть ли в DB-моделях важные поля, которых нет в schemas;
- не отражают ли поля старую marketplace-логику RentalBot;
- соответствуют ли названия полей новой логике RentalMarketBot.

---

## 2. Optional / nullable

Проверь, где schema разрешает `None`, а модель имеет `nullable=False`.

Правило:

- если поле в модели `nullable=False` и имеет `default`, то в Create-schema лучше использовать обычный тип + default;
- если поле в модели `nullable=False` и не имеет `default`, то в Create-schema поле должно быть обязательным;
- если поле в модели `nullable=True`, то в schema можно использовать `Optional[...] = None`;
- в Update-schema поля могут быть `Optional[...] = None`, потому что update частичный.

Особенно проверь:

- `Optional[...] = None` в Create-схемах для полей, которые в модели `nullable=False`;
- поля с `default` в модели, которые в Create-schema почему-то стали `Optional`;
- поля, которые могут случайно передать `None` в БД и получить NOT NULL ошибку.

---

## 3. Create / Update / Out-схемы

Проверь отдельно:

### Create schemas

- создают ли они валидный объект для БД;
- не требуют ли системные поля, которые должны выставляться автоматически;
- не разрешают ли `None` там, где БД запрещает NULL.

### Update schemas

- подходят ли они для частичного обновления;
- все ли редактируемые поля optional;
- нет ли риска записать `None` в `nullable=False` поле;
- нужно ли использовать `exclude_unset=True` или `exclude_none=True` при применении update.

### Out schemas

- содержат ли нужные поля для возврата наружу;
- используют ли `model_config = ConfigDict(from_attributes=True)`;
- не отдают ли наружу лишние внутренние поля.

---

## 4. Типы данных

Проверь:

- деньги должны быть `Decimal`, не `float`;
- datetime-поля с timezone должны быть `AwareDatetime`;
- статусы должны использовать project enums, не свободные строки;
- id-поля должны быть `int`;
- nullable FK должны быть `Optional[int]`;
- обязательные FK должны быть `int`.

---

## 5. Defaults

Проверь, что defaults в Create schemas согласованы с defaults в моделях.

Примеры:

- `nullable=False, default=True` в модели → `field: bool = True` в Create-schema;
- `nullable=False, default=0` в модели → `field: int = Field(0, ge=0)` в Create-schema;
- `nullable=True` в модели → `field: Optional[...] = None`.

---

## 6. Constraints

Проверь, что Pydantic Field-ограничения отражают базовые DB constraints:

- `String(128)` → `max_length=128`;
- `CheckConstraint("value >= 0")` → `Field(..., ge=0)`;
- `CheckConstraint("quantity >= 1")` → `Field(..., ge=1)`;
- рейтинг 1–5 → `Field(..., ge=1, le=5)`.

---

## 7. Domain semantics RentalMarketBot

Проверь, что schemas не возвращают старый смысл RentalBot:

- User = клиент, не владелец товара;
- Admin = менеджер/сотрудник компании;
- Item = товар каталога компании, не объявление пользователя;
- Rental = заявка клиента на аренду, не сделка между owner/renter;
- SupportTicket = обращение клиента;
- Review = отзыв о товаре / заявке / сервисе компании.

Опасные старые признаки:

- `owner_id`
- `renter_id`
- `user_id` внутри Item как владелец товара
- `deposit`, если его уже нет в модели
- `location`, если его уже нет в модели
- `coordinates`, если их уже нет в модели
- `RentalActorRole`
- `OWNER / RENTER`
- `handover`
- `deal`
- `listing`
- `объявление`
- `владелец`
- `арендатор`
- `сделка`

---

## 8. Relationships / nested schemas

Проверь:

- не сломаны ли вложенные схемы;
- не используются ли старые nested owner/renter outputs;
- не создают ли schemas циклические вложенности;
- правильно ли разделены краткие и подробные Out-схемы.

---

## 9. Формат ответа

Верни результат так:

### Summary

Кратко: всё хорошо / есть проблемы / есть критичные проблемы.

### KEEP

Какие schemas уже соответствуют models и RentalMarketBot.

### FIX REQUIRED

Какие строки или поля нужно исправить обязательно.

### OPTIONAL IMPROVEMENTS

Что можно улучшить, но не обязательно прямо сейчас.

### OLD MARKETPLACE SEMANTICS

Что осталось от старого RentalBot-смысла.

### PATCH PLAN

Минимальный порядок исправлений.

---

## Важно

Не переписывай schemas полностью без необходимости.

Если нужен patch, делай минимальные точечные изменения.

Не трогай:

- repositories;
- services;
- handlers;
- keyboards;
- texts.
