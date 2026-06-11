# Admin

### enum
- `class AdminActionType(str, enum.Enum)` - поле "action_type" в модели `AdminAction`
    * в БД строка, в коде строгость через Enum
    * добавляешь по мере появления

- `class AdminEntityType(str, enum.Enum)` - поле "entity_type" в модели `AdminAction`
    * в БД строка, в коде строгость через Enum


### Классификация статусов 

- `TERMINAL_STATUSES` - убрал: уже есть в `status.rental_status` (1 в 1)

- `CANCEL_STATUS_MAP`
    * Что именно означает “отмена” на этом этапе
    * (пока так: не добавляли статусы "Админ отменил", а используем эти, но в audit будет видно, что админ отменил)

- `ALLOWED_TARGETS`
  * допустимые исходы для "закрытия спора"