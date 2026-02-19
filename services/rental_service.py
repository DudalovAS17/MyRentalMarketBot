import logging
from typing import List, Optional

from db.repositories.rental import RentalRepository
#from services.item_service import ItemService
#from services.user_service import UserService
#from services.notif_service import NotificationService

from schemas.rental import RentalCreate, RentalUpdate, RentalOut, RentalWithRoleOut, RentalDetailsOut
from schemas.item import ItemOut
from schemas.user import UserOut
from utils.rental_status import is_open_status # is_terminal_status
from utils.rental_status import RentalStatus, RentalActorRole
from utils.domain_exceptions import ItemNotAvailable
from utils.errors import NotFoundError, ForbiddenError, ConflictError

logger = logging.getLogger(__name__)


class RentalService:
    """Внутренний метод смены статуса.
    Применяет строгие проверки ролей, доступа и текущего состояния сделки"""

    def __init__(
        self,
        rental_repo: RentalRepository,
        #item_service: ItemService,
        #user_service: UserService,
        #notification_service: Optional[NotificationService] = None,
    ):
        self.rental_repo = rental_repo
        #self.item_service = item_service
        #self.user_service = user_service
        #self.notification_service = notification_service

    async def get_by_id(self, rental_id: int, *, strict: bool = False) -> Optional[RentalOut]:
        """Возвращает сделку по ID"""
        rental = await self.rental_repo.get_by_id(rental_id)
        if not rental:
            if strict:
                raise NotFoundError(f"Rental not found: id={rental_id}")
            return None

        return RentalOut.model_validate(rental)

    async def list_rentals_by_user(self, user_id: int) -> List[RentalOut]:
        """Вернуть ВСЕ сделки, где пользователь арендатор или владелец."""
        rentals = await self.rental_repo.list_by_user_id(user_id)
        return [RentalOut.model_validate(r) for r in rentals]

    async def list_rentals_by_renter(self, renter_id: int) -> List[RentalOut]:
        """Возвращает все аренды, где пользователь — арендатор"""
        rentals = await self.rental_repo.list_by_renter_id(renter_id)
        return [RentalOut.model_validate(r) for r in rentals]

    async def list_rentals_by_owner(self, owner_id: int) -> List[RentalOut]:
        """Возвращает список аренд, где пользователь — владелец"""
        rentals = await self.rental_repo.list_by_owner_id(owner_id)
        return [RentalOut.model_validate(r) for r in rentals]

    async def list_user_rentals(self, user_id: int) -> List[RentalWithRoleOut]:
        """ Возвращает все сделки пользователя (как арендатор + как владелец)
        с указанием роли пользователя в каждой сделке."""

        # Получаем ВСЕ сделки, где он участвует
        rentals = await self.rental_repo.list_by_user_id(user_id) # Сортировка внутри репо

        # Размечаем каждую сделку ролями
        result: List[RentalWithRoleOut] = []
        for r in rentals:
            user_role = RentalActorRole.RENTER if r.renter_id == user_id else RentalActorRole.OWNER
            dto = RentalOut.model_validate(r, from_attributes=True)
            result.append(RentalWithRoleOut(**dto.model_dump(), user_role=user_role))

        return result

    # -------------------------------------------------------------------------------------------------------
    async def create(self, data: RentalCreate) -> RentalOut:
        """Создать новую сделку"""
        rental = await self.rental_repo.create(data)

        dto = RentalOut.model_validate(rental)
        logger.info("Rental created id=%s", dto.id)
        return dto

    async def update(self, rental_id: int, data: RentalUpdate, *, strict: bool = False) -> Optional[RentalOut]:
        """Обновление сделки"""
        obj = await self.rental_repo.update(rental_id, data)
        if not obj:
            if strict:
                raise NotFoundError(f"Сделка не найдена: id={rental_id}")
            return None

        dto = RentalOut.model_validate(obj)
        logger.info("Rental updated id=%s", dto.id)
        return dto

    async def delete(self, rental_id: int, *, strict: bool = False) -> bool:
        """Удалить сделку по id"""
        deleted = await self.rental_repo.delete(rental_id)
        if not deleted:
            if strict:
                raise NotFoundError(f"Сделка не найдена: id={rental_id}")
            return False

        logger.info("Rental deleted id=%s", rental_id)
        return True

    # -------------------------------------------------------------------------------------------------------

    async def get_rental_details(
            self,
            rental_id: int,
            current_user_id: int,
            *,
            strict: bool = False
    ) -> Optional[RentalDetailsOut]:
        """Возвращает подробную информацию о сделке.
        Доступ разрешён только арендатору или владельцу сделки."""

        # Убрали, чтобы убрать зависимость от других сервисов. Работаем через get_details_by_id()
        #rental = await self.rental_repo.get_by_id(rental_id)
        rental = await self.rental_repo.get_details_by_id(rental_id)
        # теперь item -> rental.item, owner -> rental.owner и т.д.

        if not rental:
            if strict:
                raise NotFoundError(f"Сделка не найдена: id={rental_id}")
            return None

        # Проверяем право доступа
        if current_user_id not in (rental.renter_id, rental.owner_id):
            #logger.warning(f"Пользователь {current_user_id} пытался получить доступ к чужой сделке {rental_id}")
            if strict:
                raise ForbiddenError("Нет доступа к сделке")
            return None

        # Подгружаем товар
        #item = await self.item_service.get_item_by_id(rental.item_id)

        # Подгружаем участников
        #renter = await self.user_service.get_by_id(rental.renter_id)
        #owner = await self.user_service.get_by_id(rental.owner_id)

        # ORM —> DTO
        item_dto = ItemOut.model_validate(rental.item) # if item else None
        renter_dto = UserOut.model_validate(rental.renter) # if renter else None
        owner_dto = UserOut.model_validate(rental.owner) # if owner else None
        if not rental.item or not rental.renter or not rental.owner:
            if strict:
                raise NotFoundError("Не удалось собрать детали сделки (связанные сущности не найдены)")
            return None

        # Определяем роль пользователя
        role = RentalActorRole.RENTER if rental.renter_id == current_user_id else RentalActorRole.OWNER

        # Возвращаем DTO (без форматирования)
        return RentalDetailsOut(
            id=rental.id,
            rental=RentalOut.model_validate(rental),
            item=item_dto,
            renter=renter_dto,
            owner=owner_dto,
            user_role=role
        )


    # =======================  STATUS MANAGEMENT — ядро бизнес-логики  ====================================
    async def _transition(self,*, rental_id: int, actor_user_id: int,
                          actor_role: RentalActorRole,
                          expected_status: RentalStatus,
                          new_status: RentalStatus,
                          strict: bool = False,
                          err_msg: str | None = None,
    ) -> bool:
        ok = await self.rental_repo.try_update_status(
            rental_id=rental_id,
            new_status=new_status,
            expected_status=expected_status,
            actor_user_id=actor_user_id,
            actor_role=actor_role,
        )

        logger.info(
            "rental.status_transition rental_id=%s actor_id=%s role=%s %s→%s ok=%s",
            rental_id, actor_user_id, actor_role.value, expected_status.value, new_status.value, ok
        )

        if not ok and strict:
            who = "владелец" if actor_role == RentalActorRole.OWNER else "арендатор"
            diag = f"({expected_status.value} → {new_status.value}): статус изменился или {who} не имеет прав"
            message = f"{err_msg}. {diag}" if err_msg else f"Нельзя выполнить действие {diag}"
            # без детализации причины:
            raise ConflictError(message)

        return ok

    # Переход: REQUESTED → CONFIRMED
    async def confirm_requested(self, *, rental_id: int, owner_id: int, strict: bool = False) -> bool:
        """Подтвердить REQUESTED → CONFIRMED может только владелец"""
        return await self._transition(
            rental_id=rental_id,
            actor_user_id=owner_id,
            actor_role=RentalActorRole.OWNER,
            expected_status=RentalStatus.REQUESTED,
            new_status=RentalStatus.CONFIRMED,
            strict=strict,
            err_msg="Нельзя подтвердить запрос на аренду"
        )

    # REQUESTED → REJECTED_BY_OWNER
    async def reject_requested_by_owner(self, *, rental_id: int, owner_id: int, strict: bool = False) -> bool:
        """REQUESTED → REJECTED (владелец отклоняет)"""
        return await self._transition(
            rental_id=rental_id,
            actor_user_id=owner_id,
            actor_role=RentalActorRole.OWNER,
            expected_status=RentalStatus.REQUESTED,
            new_status=RentalStatus.REJECTED_BY_OWNER,
            strict=strict,
            err_msg="Нельзя отклонить запрос на аренду"
        )

    # REQUESTED → REJECTED_BY_RENTER
    async def reject_requested_by_renter(self, *, rental_id: int, renter_id: int, strict: bool = False) -> bool:
        """REQUESTED → CANCELLED_BY_RENTER (арендатор отменяет)"""
        return await self._transition(
            rental_id=rental_id,
            actor_user_id=renter_id,
            actor_role=RentalActorRole.RENTER,
            expected_status=RentalStatus.REQUESTED,
            new_status=RentalStatus.REJECTED_BY_RENTER,
            strict=strict,
            err_msg="Нельзя отменить запрос на аренду"
        )

    # CONFIRMED → CANCELLED_CONFIRMED_BY_OWNER
    async def cancel_confirmed_by_owner(self, *, rental_id: int, owner_id: int, strict: bool = False) -> bool:
        """Владелец отклоняет утвержденную аренду"""
        return await self._transition(
            rental_id=rental_id,
            actor_user_id=owner_id,
            actor_role=RentalActorRole.OWNER,
            expected_status=RentalStatus.CONFIRMED,
            new_status=RentalStatus.CANCELLED_CONFIRMED_BY_OWNER,
            strict=strict,
            err_msg="Нельзя отменить утвержденную аренду"
        )

    # CONFIRMED → CANCELLED_CONFIRMED_BY_RENTER
    async def cancel_confirmed_by_renter(self, *, rental_id: int, renter_id: int, strict: bool = False) -> bool:
        """Арендатор отклоняет утвержденную аренду"""
        return await self._transition(
            rental_id=rental_id,
            actor_user_id=renter_id,
            actor_role=RentalActorRole.RENTER,
            expected_status=RentalStatus.CONFIRMED,
            new_status=RentalStatus.CANCELLED_CONFIRMED_BY_RENTER,
            strict=strict,
            err_msg="Нельзя отменить утвержденную аренду"
        )

    # CONFIRMED → ACTIVE
    async def start_rental(self, *, rental_id: int, owner_id: int, strict: bool = False) -> bool:
        """начало аренды [в будущем автоматически по дате]"""
        return await self._transition(
            rental_id=rental_id,
            actor_user_id=owner_id,
            actor_role=RentalActorRole.OWNER,
            expected_status=RentalStatus.CONFIRMED,
            new_status=RentalStatus.ACTIVE,
            strict=strict,
            err_msg="Нельзя начать аренду"
        )

    # ACTIVE → COMPLETED
    async def complete_active(self, *, rental_id: int, owner_id: int, strict: bool = False) -> bool:
        """Владелец завершает аренду = возврат вещи (можно сделать и арендатором)"""
        return await self._transition(
            rental_id=rental_id,
            actor_user_id=owner_id,
            actor_role=RentalActorRole.OWNER,
            expected_status=RentalStatus.ACTIVE,
            new_status=RentalStatus.COMPLETED,
            strict=strict,
            err_msg="Нельзя завершить аренду"
        )

    # ACTIVE → CANCELLED_BY_OWNER
    async def cancel_active_by_owner(self, *, rental_id: int, owner_id: int, strict: bool = False) -> bool:
        """ACTIVE → CANCELLED_BY_OWNER (отмена активной аренды владельцем)"""
        return await self._transition(
            rental_id=rental_id,
            actor_user_id=owner_id,
            actor_role=RentalActorRole.OWNER,
            expected_status=RentalStatus.ACTIVE,
            new_status=RentalStatus.CANCELLED_BY_OWNER,
            strict=strict,
            err_msg="Нельзя отменить активную аренду владельцем"
        )

    # ACTIVE → CANCELLED_BY_RENTER
    async def cancel_active_by_renter(self, *, rental_id: int, renter_id: int, strict: bool = False) -> bool:
        """ACTIVE → CANCELLED_BY_RENTER (отмена активной аренды арендатором)"""
        return await self._transition(
            rental_id=rental_id,
            actor_user_id=renter_id,
            actor_role=RentalActorRole.RENTER,
            expected_status=RentalStatus.ACTIVE,
            new_status=RentalStatus.CANCELLED_BY_RENTER,
            strict=strict,
            err_msg="Нельзя отменить активную аренду арендатором"
        )

    # ACTIVE → DISPUTED
    async def open_dispute(self, *, rental_id: int, actor_id: int, strict: bool = False) -> bool:
        """ Открыть спор: может owner или renter"""

        """ Если:
        👉 “Хочу разрешить переход в DISPUTED не только из ACTIVE, но и из CONFIRMED (и возможно из COMPLETED). 
        Тогда надо проверять expected_status по нескольким вариантам.” То надо через:
            allowed_from = (RentalStatus.CONFIRMED, RentalStatus.ACTIVE)  # при желании добавь COMPLETED
            for expected in allowed_from:
        """

        ok = await self.rental_repo.try_update_status_if_participant(
            rental_id=rental_id,
            new_status=RentalStatus.DISPUTED,
            expected_status=RentalStatus.ACTIVE,
            actor_user_id=actor_id)

        if not ok and strict:
            raise ConflictError("Нельзя открыть спор: нет прав или статус уже изменился")
        return ok

    # -------------------------------------
    async def confirm_handover_by_owner(self, *, rental_id: int, owner_id: int, strict: bool = False) -> bool:
        """Владелец нажал 'Передал вещь' (CONFIRMED)"""
        ok = await self.rental_repo.try_set_owner_handover_confirmed(rental_id=rental_id, owner_id=owner_id)

        if not ok:
            if strict:
                raise ConflictError( # ?
                    "Нельзя подтвердить передачу вещи: статус изменился, нет прав, или действие уже подтверждено"
                )
            return False

        # если арендатор уже подтвердил получение — активируем
        await self.rental_repo.activate_if_ready(rental_id=rental_id)
        return True

    async def confirm_receive_by_renter(self, *, rental_id: int, renter_id: int, strict: bool = False) -> bool:
        """Арендатор нажал 'Получил вещь' (CONFIRMED)"""
        ok = await self.rental_repo.try_set_renter_confirm_receive(rental_id=rental_id, renter_id=renter_id)
        if not ok:
            if strict:
                raise ConflictError( # ?
                    "Нельзя подтвердить получение вещи: статус изменился, нет прав, или действие уже подтверждено"
                )
            return False

        # если владелец уже подтвердил передачу — активируем
        await self.rental_repo.activate_if_ready(rental_id=rental_id)
        return True
    # ---------------------------------------

    # !!!!!!!!!!!!!!!!!!!!!!!!!!!Тут пока остановился!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    # ===================  ADMIN MANAGEMENT — админка  ===============================
    async def get_open_rental_for_item(self, item_id: int): # -> Optional[RentalOut]
        """Возвращает первую открытую аренду для item_id или None"""
        rentals = await self.rental_repo.list_recent_open_by_item_id(item_id)
        for r in rentals:
            if is_open_status(r.status):
                return r # RentalOut.model_validate(r)
        return None

    # Для доменной проверки (будет ниже) лучше работать с моделью БД Rental, без Pydantic-валидации (RentalOut).
    # Это быстрее и проще, и меньше шансов на “почему end_date не того типа”.

    async def ensure_item_available(self, item_id: int) -> None:
        """Доменная гарантия: item нельзя арендовать, если есть открытая аренда"""
        open_rental = await self.get_open_rental_for_item(item_id)
        if not open_rental:
            return

        raise ItemNotAvailable(
            item_id=item_id,
            rental_id=open_rental.id,
            status=open_rental.status.value, # Enum -> str
            end_date=open_rental.end_date.isoformat(), # aware datetime -> str ???
        )


# возможный будущий апгрейд этого сервиса
"""
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
"""
