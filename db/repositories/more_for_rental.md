## Тут дальнейшее расширение связанное с уведомлениями

```
@staticmethod
    def _change_rental_status(
        rental_id: int,
        user_id: int,
        allowed_roles: List[str],
        allowed_current_statuses: List[RentalStatus],
        new_status: RentalStatus,
        action_name: str,
        # Параметры для уведомлений
        notify_recipient_role: Optional[str] = None,  # 'renter', 'owner', 'other'
        notify_message_template: Optional[str] = None,
        notify_button_text: Optional[str] = None,
        notify_button_callback_action: Optional[str] = None
    ) -> bool:
    ""Внутренний вспомогательный метод для изменения статуса аренды и отправки уведомления.""

    logger.warning(f"{action_name}: Аренда {rental_id} не найдена.")
    logger.warning(f"{action_name}: Пользователь {user_id} (роль: {current_user_role}) не "
                   f"имеет прав для действия с арендой {rental_id}. Требуется роль: {allowed_roles}")
    logger.warning(f"{action_name}: Недопустимый текущий статус {rental.status.value} "
                   f"для аренды {rental_id}. Допустимые: {[s.value for s in allowed_current_statuses]}")
    logger.info(f"{action_name}: Статус аренды {rental_id} успешно изменен с {original_status.value} "
                f"на {new_status.value} пользователем {user_id}")
    logger.error(f"Ошибка при выполнении {action_name} для аренды {rental_id}: {e}", exc_info=True)

    try:
        rental =

        # Определяем роль текущего пользователя
        current_user_role = "renter"/"owner"

        # Проверка прав
        if current_user_role not in allowed_roles:

        # Проверка текущего статуса
        if rental.status not in allowed_current_statuses:

        # Обновляем статус
        rental.status = new_status

    # Отправка уведомления (если статус успешно изменен и параметры заданы)
    if success and notify_recipient_role and notify_message_template and rental:  # Убедимся, что rental не None
        recipient_id = None
        if notify_recipient_role == 'renter':
            recipient_id = rental.renter_id
        elif notify_recipient_role == 'owner':
            recipient_id = rental.owner_id
        elif notify_recipient_role == 'other':
            # Определяем ID другой стороны
            recipient_id = rental.owner_id if current_user_role == 'renter' else rental.renter_id

        if recipient_id and recipient_id != user_id:  # Не отправляем уведомление самому себе
            # Получаем имя товара для уведомления
            item_name = None
            try:
                item = ItemRepository.get_item_by_id(db, rental.item_id)
                if item: item_name = item.name
            except Exception as item_err:
                logger.error(
                    f"Не удалось получить имя товара {rental.item_id} для уведомления по аренде {rental_id}: {item_err}")

            # Отправляем уведомление
            RentalService._send_rental_notification(
                db=db,
                rental_id=rental_id,
                recipient_id=recipient_id,
                message_template=notify_message_template,
                item_name=item_name,
                button_text=notify_button_text,
                button_callback_action=notify_button_callback_action
            )
        else:
            logger.debug(
                f"Уведомление по аренде {rental_id} не отправлено (получатель: {recipient_id}, инициатор: {user_id}).")


    @staticmethod
    @with_db_session(commit=True)
    def confirm_rental(rental_id: int, user_id: int, db=None) -> bool:
        ""Владелец подтверждает запрос на аренду.""
        return RentalService._change_rental_status(
            rental_id=rental_id,
            user_id=user_id,
            allowed_roles=["owner"],
            allowed_current_statuses=[RentalStatus.REQUESTED],
            new_status=RentalStatus.CONFIRMED,
            action_name="confirm_rental",
            notify_recipient_role='renter',
            notify_message_template="✅ Ваш запрос на аренду товара {item_name} подтвержден владельцем!",
            notify_button_text="🔍 Посмотреть сделку"
        )

```

---

### Старая функция 

```    
async def get_by_user_id_with_filters(
    self,
    user_id: int,
    *,
    as_renter: bool = True, # Включить аренды, где пользователь является арендатором
    as_owner: bool = True, # Включить аренды, где пользователь является владельцем
    status_filter: Optional[List[RentalStatus]] = None, # Список статусов для фильтрации (None - все статусы)
    order_by_creation: bool = True, # Сортировать ли по убыванию даты создания
) -> List[Rental]:
    ""Получает список аренд для указанного пользователя (где пользователь арендатор и/или владелец)""
    async with self._sf() as s:
        stmt = select(Rental)

        # Фильтрация по роли
        role_conditions = []
        if as_renter:
            role_conditions.append(Rental.renter_id == user_id)
        if as_owner:
            role_conditions.append(Rental.owner_id == user_id)
        # если as_renter=True, as_owner=True → [Rental.renter_id == 42, Rental.owner_id == 42]

        if role_conditions:
            stmt = stmt.where(or_(*role_conditions))
            ""or_ — для объединения условий через OR
               * - «раскрывает» список
            то есть если список [A, B] → в SQL превратится в (A OR B), 
            а именно WHERE (renter_id = 42 OR owner_id = 42)""
        else:
            logger.warning(
                "get_by_user_id_with_filters() — роль не указана, возвращаем пустой список"
            )
            return []

        # Фильтр по статусам
        if status_filter:
            valid_statuses = [status for status in status_filter if isinstance(status, RentalStatus)]
            ""Берём первый элемент → RentalStatus.ACTIVE → он isinstance(..., RentalStatus) → ✅ добавляем.
            Второй элемент → "ошибка" → это str, а не RentalStatus → ❌ пропускаем.
            Третий элемент → RentalStatus.CONFIRMED → ✅ добавляем.""
            if valid_statuses:
                stmt = stmt.where(Rental.status.in_(valid_statuses))
                # Rental.status → это колонка status в таблице rentals
                # То есть мы достаём только те сделки, у которых статус входит в список valid_statuses
            else:
                logger.warning(
                    "get_by_user_id_with_filters() — передан некорректный статус фильтра"
                )

        # Сортировка
        if order_by_creation:
            stmt = stmt.order_by(Rental.created_at.desc())
            # .desc() → убывающий порядок (новые записи первыми)

        res = await s.execute(stmt)
        return list(res.scalars().all())
```