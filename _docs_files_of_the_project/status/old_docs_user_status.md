# User

- `class AccountStatus(enum.Enum)` - (enum) Статусы состояния аккаунта пользователя
- `ALLOWED_STATUS_TRANSITIONS` - таблица допустимых переходов
- `can_transition` - функция проверки перехода

Было: 
```
ALLOWED_STATUS_TRANSITIONS: dict[AccountStatus, set[AccountStatus]] = {
    AccountStatus.ACTIVE: {AccountStatus.BANNED},
    AccountStatus.BANNED: {AccountStatus.ACTIVE}
}
```