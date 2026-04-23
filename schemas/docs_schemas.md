## Category

> [CategoryCreate]() - Схема для создания категории/подкатегории

- `name: Optional[str] = Field(None, min_length=1, max_length=128)`

> [CategoryUpdate]() - Схема для обновления категории/подкатегории

> [CategoryOut]() - Схема для возврата данных о категории наружу

- `created_at: AwareDatetime` (было `Optional[datetime] = None`)
- `updated_at: AwareDatetime` (`Optional[datetime] = None`)

---

## Item

> [ItemCreate]() - Схема для создания объявления

- `price: Decimal = Field(..., ge=0)` - [цена ≥ 0]() (тоже для `deposit`)

- `min_rental_period: int = Field(1, ge=1)` - [минимум 1 день]()

- `validate_coordinates()` - у нас в Модели coordinates = JSON (слишком широко), поэтому делаем этот валидатор

- `photos: Optional[List[str]] = None` - тут наверно не нужно

```
Это админские поля, не пользовательские -> убираем из Create
- is_featured: bool = False
- status: ItemStatus = ItemStatus.PENDING
```

> [ItemUpdate]() - Схема для обновления объявления (только изменяемые поля)

- `is_available: Optional[bool] = None` - убираем

> [ItemOut]() - Схема для возврата данных об объявлении

- Убрал: `is_available: bool = True` - default установлен моделью
- `views_count` и `orders_count` - default установлен моделью
- `created_at` и `updated_at` - [AwareDatetime]() (было: `Optional[datetime] = None`)

> [ItemModerationUpdate]() - для Админов: схема для обновления объявления

- `moderated_by_admin_id` и `moderated_at` - убираем: ставятся сервисом автоматически
- `is_featured` - default установлен моделью

Если так: `ItemModerationUpdate(ItemUpdate)`, т.е. все поля из `ItemUpdate` тут тоже будут (унаследовали), 
то админ может менять всё, что может пользователь (`title/price/…`), но пока сделаем чтобы не мог.

> [ItemAdminOut(ItemOut)]() - Админская схема для возврата данных об объявлении

- все поля из `ItemOut` тут тоже будут - унаследовали

> [ItemCreateDraft]() - Черновик для FSM (пошаговое заполнение)

- `model_config = ConfigDict(extra="forbid")` - 🚫 запрет лишних полей

---

## Rental

> [RentalCreate]() - Схема для создания сделки аренды
- Убрал `status: RentalStatus = RentalStatus.REQUESTED`, т.к. дефолт устанавливает модель, 
а "создавать" статус нелогично.

> [RentalUpdate]() - Схема для обновления сделки (только изменяемые поля)
- Убрал `status: Optional[RentalStatus] = None` по той же причины, что и выше

> [RentalOut]() - Схема для возврата сделки наружу
- Для `created_at`/`updated_at` делаем `AwareDatetime` или `Optional[AwareDatetime] = None`?

В этих трех везде было `datetime` для `start_date` и `end_date` - заменил на `AwareDatetime`.
`AwareDatetime` - `datetime`, у которого ОБЯЗАТЕЛЬНО есть `tz_info` (т.е. `timezone-aware`)

> [RentalWithRoleOut(RentalOut)]() - Схема для возврата сделки наружу с указанием роли текущего пользователя в сделке

> [RentalDetailsOut]() - Схема для возврата полной информации о сделке наружу, включая объявление, арендатора, 
    владельца и роль текущего пользователя

> [RentalAdminDetailsOut]() - Схема для возврата полной информации о сделке наружу для администратора

> [RentalCreateDraft]() - FSM-черновик для создания сделки аренды. 
    Поля совпадают с RentalCreate, но start/end/total могут быть пустыми до выбора дат.
- тут `start_date` и `end_date` - хранятся как строки! ([DD.MM.YYYY]())

- Убрал `status: RentalStatus = RentalStatus.REQUESTED` - статус не может задаваться

---

## User

> [UserCreate]() - Схема для создания пользователя
- Убрал: устанавливаются автоматически сервисом/БД
    * `rating` и `rating_count`
    * `account_status: AccountStatus = AccountStatus.ACTIVE`

> [UserUpdate]() - Схема для обновления пользователя

> [UserOut]() - Схема для возврата данных о пользователе наружу

> [UserAdminUpdate]() - Схема для админского обновления пользователя
- `account_status: Optional[AccountStatus] = None` - лучше убрать?
- надо обдумать поля

---

## Admin

> [AdminActionCreate]() - Схема для записи audit-действия админа (создание)

> [AdminActionOut]() - Схема для возврата audit-записи наружу

---

## Photo

> [PhotoCreate]() - Схема для создания фото
- Убрал `item_id: int = Field(...)` - приходит из контекста
    * description="ID объявления, к которому относится фото"
- Убрал `order: Optional[int] = Field(None, ge=0)`
    * description="Порядок отображения фото"

??`order` может быть не указан — тогда сервис сам подставит следующий??

> Убрал [PhotoUpdate]() - Частичное обновление фото. Там было только:
- `telegram_file_id: Optional[str] = Field(None, max_length=500)`
- `order: Optional[int] = Field(None, ge=0)`

> [PhotoOut]() - Схема для возврата данных о фото наружу

---

## Review

> [ReviewCreate]() - Схема для создания отзыва

- Было: `reviewer_id: int` - из контекста авторизации или из Telegram-пользователя, но в сервисе
- Было: `reviewee_id: int` - всегда определяется сделкой

> [ReviewUpdate]() - Схема для обновления отзыва
- Убрал: пока запрещаем вмешательство в отзыв
- Было: `rating: Optional[int] = Field(default=None, ge=1, le=5)`
- Было: `comment: Optional[str] = None`

> [ReviewOut]() - Схема для возврата отзыва наружу

---

## SupportTicket

> [SupportTicketCreate]() - Создание тикета поддержки пользователем
- `telegram_id` и `username` устанавливает сервис

> [SupportTicketUpdate]() - Обновление тикета пользователем
- Убрал: запрещаем
- Было: `text: Optional[str] = None`

> [SupportTicketOut]() - Возврат тикета поддержки наружу (пользователь / админ)

- Статус всегда OPEN при создании `status: SupportTicketStatus = SupportTicketStatus.OPEN`. 
Смена статуса должна происходить только через доменные методы: close_ticket / reopen_ticket

> [SupportTicketCreateInternal]() - Внутренняя схема для создания тикета поддержки из данных пользователя и текста обращения