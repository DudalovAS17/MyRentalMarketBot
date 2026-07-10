## возможный будущий апгрейд этого сервиса

```
class RentalService:
    ""Сервис для работы со сделками аренды""

    class NotifyButton(TypedDict, total=False):
        text: str
        callback_data: str

    # notify_cb: (recipient_id, message, button|None) -> None
    def __init__(
        self,
        repo: RentalRepository,
        item_repo: Optional[ItemRepository] = None,
        user_repo: Optional[UserRepository] = None,
        notify_cb: Optional[Callable[[int, str, Optional["RentalService.NotifyButton"]], None]] = None,
    ) -> None:
        self.repo = repo
        self.item_repo = item_repo
        self.user_repo = user_repo
        self._notify = notify_cb

    # ---------- ВСПОМОГАТЕЛЬНО ----------

    @staticmethod
    def get_status_text(status: str | RentalStatus) -> str:
        ""Возвращает человекочитаемый текст статуса сделки""
        # Нормализуем к строке-значению enum
        key = status.value if isinstance(status, RentalStatus) else str(status).lower()

        mapping = {
            "requested": "⏳ Запрошена",
            "confirmed": "✅ Подтверждена",
            "active": "▶️ Активна",
            "completed": "🏁 Завершена",
            "cancelled": "❌ Отменена",
            "rejected": "🚫 Отклонена",
            "disputed": "⚠️ Спор",
            "payment_pending": "💰 Ожидает оплаты",
        }
        return mapping.get(key, "Неизвестный статус")

    def _send_notification(
        self,
        *,
        recipient_id: int,
        message_template: str,
        rental_id: int,
        item_name: Optional[str],
        button_text: Optional[str] = "🔍 Посмотреть детали",
        button_callback_action: Optional[str] = None,
    ) -> None:
        ""Отправляет уведомление через переданный при инициализации notify_cb (если он есть).""
        if not self._notify:
            return
        name = f"'{item_name}'" if item_name else "(название неизвестно)"
        message = message_template.format(item_name=name, rental_id=rental_id)
        button: Optional[RentalService.NotifyButton] = None
        if button_text:
            button = {
                "text": button_text,
                "callback_data": button_callback_action or f"rental_details:{rental_id}",
            }
        try:
            self._notify(recipient_id, message, button)
            logger.info("Уведомление отправлено пользователю %s по сделке %s", recipient_id, rental_id)
        except Exception as e:
            logger.error("Не удалось отправить уведомление пользователю %s: %s", recipient_id, e, exc_info=True)

    def _change_status(
        self,
        *,
        rental_id: int,
        user_id: int,
        allowed_roles: List[str],
        allowed_current_statuses: Optional[List[RentalStatus]],
        new_status: RentalStatus,
        action_name: str,
        notify_recipient_role: Optional[str] = None,  # 'renter' | 'owner' | 'other'
        notify_message_template: Optional[str] = None,
        notify_button_text: Optional[str] = None,
        notify_button_callback_action: Optional[str] = None,
    ) -> bool:
        ""
        Универсальный метод смены статуса сделки с проверкой роли/текущего статуса и опциональным уведомлением.
        Возвращает True при успехе.
        ""
        rental = self.repo.get_by_id(rental_id)
        if not rental:
            logger.warning("%s: сделка %s не найдена", action_name, rental_id)
            return False

        # Роль инициатора
        role = "owner" if rental.owner_id == user_id else "renter" if rental.renter_id == user_id else None
        if role not in allowed_roles:
            logger.warning("%s: у пользователя %s нет прав для сделки %s (роль=%s)", action_name, user_id, rental_id, role)
            return False

        # Проверка допустимого текущего статуса (если задан)
        if allowed_current_statuses and rental.status not in allowed_current_statuses:
            logger.warning(
                "%s: недопустимый текущий статус %s для сделки %s. Разрешено: %s",
                action_name, rental.status.value, rental_id, [s.value for s in allowed_current_statuses],
            )
            return False

        # Обновляем статус
        updated = self.update(rental_id, RentalUpdate(status=new_status))
        if not updated:
            logger.error("%s: не удалось обновить статус сделки %s → %s", action_name, rental_id, new_status.value)
            return False

        logger.info("%s: статус сделки %s изменен на %s пользователем %s", action_name, rental_id, new_status.value, user_id)

        # Уведомление (если задано)
        if notify_recipient_role and notify_message_template:
            # Определяем получателя
            if notify_recipient_role == "renter":
                recipient_id = rental.renter_id
            elif notify_recipient_role == "owner":
                recipient_id = rental.owner_id
            else:  # 'other' — другая сторона
                recipient_id = rental.owner_id if role == "renter" else rental.renter_id

            if recipient_id != user_id:
                # Имя вещи для уведомления
                item_name = None
                if self.item_repo:
                    try:
                        item = self.item_repo.get_by_id(rental.item_id)
                        item_name = getattr(item, "title", None)
                    except Exception as e:
                        logger.error("Ошибка получения вещи %s для уведомления по сделке %s: %s", rental.item_id, rental_id, e)

                self._send_notification(
                    recipient_id=recipient_id,
                    message_template=notify_message_template,
                    rental_id=rental_id,
                    item_name=item_name,
                    button_text=notify_button_text,
                    button_callback_action=notify_button_callback_action,
                )

        return True

    # ---------- ШОРТКАТЫ СТАТУСОВ ----------

    confirm_rental(Владелец подтверждает запрос на аренду):
        _change_status(
            notify_recipient_role="renter",
            notify_message_template="✅ Ваш запрос на аренду товара {item_name} подтвержден владельцем.",
            notify_button_text="🔍 Посмотреть сделку",
        )

    reject_rental (Владелец отклоняет запрос): 
        _change_status(
            notify_recipient_role="renter",
            notify_message_template="🚫 Ваш запрос на аренду товара {item_name} отклонен владельцем.",
            notify_button_text="🔍 Посмотреть детали",
        )

    start_rental (Владелец запускает аренду (передал вещь)):
        _change_status(
            notify_message_template="▶️ Аренда товара {item_name} началась.",
            notify_button_text="🔍 Посмотреть детали",
        )

    complete_rental (Владелец завершает аренду (вещь возвращена)):
        _change_status(
            notify_recipient_role="renter",
            notify_message_template="🏁 Аренда товара {item_name} завершена. Спасибо за использование сервиса!",
            notify_button_text="⭐ Оставить отзыв",
            notify_button_callback_action=f"rental_action:review:{rental_id}",
        )

    cancel_rental_request(Арендатор отменяет свой запрос):
        _change_status(
            notify_recipient_role="owner",
            notify_message_template="⚠️ Арендатор отменил запрос на аренду вашего товара {item_name}.",
            notify_button_text="🔍 Посмотреть детали",
        )

    cancel_confirmed_rental(Отмена подтверждённой, но не начатой аренды любой стороной):
        _change_status(
            notify_recipient_role="other",
            notify_message_template=f"🚫 Сделка по аренде товара {{item_name}} была отменена {initiator}.",
            notify_button_text="🔍 Посмотреть детали",
        )

    start_dispute(Открыть спор → DISPUTED (обычно из ACTIVE/COMPLETED)):
        _change_status(
            rental_id=rental_id,
            user_id=user_id,
            allowed_roles=["renter", "owner"],
            allowed_current_statuses=[RentalStatus.ACTIVE, RentalStatus.COMPLETED],
            new_status=RentalStatus.DISPUTED,
            action_name="start_dispute",
            notify_recipient_role="other",
            notify_message_template="⚠️ По сделке {item_name} открыт спор.",
            notify_button_text="🔍 Посмотреть детали",
        )
```
