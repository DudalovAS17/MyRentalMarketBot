import logging
from datetime import datetime
from typing import List, Optional



from services.item_service import ItemService
from services.user_service import UserService
from services.notif_service import NotificationService
from db.repositories.rental import RentalRepository
from db.models.rental import RentalStatus #,  Rental
from schemas.rental import RentalCreate, RentalUpdate, RentalOut

from keyboards.rental_kb import get_open_rental_keyboard
from utils.rental_status import is_terminal_status, is_open_status
from utils.domain_exceptions import ItemNotAvailable

logger = logging.getLogger(__name__)


class RentalService:
    """Внутренний метод смены статуса.
    Применяет строгие проверки ролей, доступа и текущего состояния сделки"""

    def __init__(
        self,
        rental_repo: RentalRepository,
        item_service: ItemService,
        user_service: UserService,
        notification_service: Optional[NotificationService] = None,
    ):
        self.rental_repo = rental_repo
        self.item_service = item_service
        self.user_service = user_service
        self.notification_service = notification_service

    async def get_by_id(self, rental_id: int) -> Optional[RentalOut]:
        """Возвращает сделку по ID"""
        rental = await self.rental_repo.get_by_id(rental_id)
        return RentalOut.model_validate(rental) if rental else None

    async def get_rentals_by_user(self, user_id: int) -> List[RentalOut]:
        """Вернуть ВСЕ сделки, где пользователь арендатор или владелец."""
        rentals = await self.rental_repo.get_by_user_id(user_id)
        return [RentalOut.model_validate(r) for r in rentals]

    async def get_rentals_by_renter(self, renter_id: int) -> List[RentalOut]:
        """Возвращает все аренды, где пользователь — арендатор"""
        rentals = await self.rental_repo.get_by_renter_id(renter_id)
        return [RentalOut.model_validate(r) for r in rentals]

    async def get_rentals_by_owner(self, owner_id: int) -> List[RentalOut]:
        """Возвращает список аренд, где пользователь — владелец"""
        rentals = await self.rental_repo.get_by_owner_id(owner_id)
        return [RentalOut.model_validate(r) for r in rentals]

    async def get_user_rentals(self, user_id: int) -> List[dict]:
        """
        Возвращает все сделки пользователя (как арендатор + как владелец)
        с указанием роли пользователя в каждой сделке.

        {...данные сделки...,
            "user_role": "renter" | "owner"}
        """

        # 1. Получаем ВСЕ сделки, где он участвует
        rentals = await self.rental_repo.get_by_user_id(user_id)

        result: list[dict] = []

        # 2. Размечаем каждую сделку ролями
        for r in rentals:
            user_role = "renter" if r.renter_id == user_id else "owner"
            d = r.to_dict() # RentalOut.model_validate(r).model_dump()
            d["user_role"] = user_role
            result.append(d)

        # 3. Сортировка: новые вверх (по created_at)
        result.sort(
            key=lambda x: x.get("created_at") or datetime.min, # x: x["created_at"]
            reverse=True
        )
        return result

    async def create_rental(self, data: RentalCreate) -> RentalOut:
        """Создать новую сделку аренды."""
        rental = await self.rental_repo.create(data)
        #return RentalOut.model_validate(rental)
        # ---------------------------------- Notification logic --------------------------------------------
        rental_out = RentalOut.model_validate(rental)

        # уведомление владельцу товара о новом запросе
        if self.notification_service:
            item = await self.item_service.get_item_by_id(rental.item_id)
            renter = await self.user_service.get_by_id(rental.renter_id)

            item_title = getattr(item, "title", "—")
            renter_display = str(rental.renter_id)
            renter_username = getattr(renter, "username", None)
            if renter_username:
                renter_display = f"@{renter_username}"

            text = (
                " 🔔 Новая заявка на аренду\n"
                f" 📩 Объявление: {item_title}\n"
                f" 👤 Арендатор: {renter_display}"
            )
            await self.notification_service.notify_user(
                rental.owner_id,
                text,
                reply_markup=get_open_rental_keyboard(rental.id),
            )
        # -------------------------------------------------------------------------------------------------------

        return rental_out

    async def update_rental(self, rental_id: int, data: RentalUpdate) -> Optional[RentalOut]:
        """Обновление сделки (общий метод)."""
        updated = await self.rental_repo.update(rental_id, data)
        return RentalOut.model_validate(updated) if updated else None

    async def delete_rental(self, rental_id: int) -> bool:
        return await self.rental_repo.delete(rental_id)



    async def get_rental_details(self, rental_id: int, current_user_id: int) -> Optional[dict]:
        """Возвращает подробную информацию о сделке.
        Доступ разрешён только арендатору или владельцу сделки."""

        # 1️⃣ Получаем сделку
        rental = await self.rental_repo.get_by_id(rental_id)
        if not rental:
            logger.warning(f"[Rental_details] сделка {rental_id} не найдена")
            return None

        # 2️⃣ Проверяем право доступа
        if current_user_id not in (rental.renter_id, rental.owner_id):
            logger.warning(
                f"[Rental_details] Пользователь {current_user_id} пытался получить доступ к чужой сделке {rental_id}"
            )
            return None

        # 3️⃣ Подгружаем товар
        item = await self.item_service.get_item_by_id(rental.item_id)

        # 4️⃣ Подгружаем участников
        renter = await self.user_service.get_by_id(rental.renter_id)
        owner = await self.user_service.get_by_id(rental.owner_id)

        # 5️⃣ Определяем роль пользователя
        role = "renter" if rental.renter_id == current_user_id else "owner"

        # 6️⃣ Формируем единый словарь
        details = {
            "id": rental.id,
            "item": {
                "id": item.id if item else None,
                "title": getattr(item, "title", "Неизвестный товар"),
                "description": getattr(item, "description", "-"),
                "price": getattr(item, "price", 0),
                "deposit": getattr(item, "deposit", 0),
                "location": getattr(item, "location", "-"),
                #"photos": getattr(item, "photos", []), # !!! Фото лучше тянуть через PhotoService/Repository.
            },
            "renter": {
                "id": renter.id if renter else None,
                "full_name": renter.full_name if renter else "Неизвестный арендатор",
                #"full_name": renter.full_name if renter and renter.full_name else (
                #    renter.first_name if renter else "—"),
                "username": renter.username if renter else None,
                "phone": renter.phone if renter else None,
            },
            "owner": {
                "id": owner.id if owner else None,
                "full_name": owner.full_name if owner else "Неизвестный владелец",
                # "full_name": renter.full_name if renter and renter.full_name else (
                #    renter.first_name if renter else "—"),
                "username": owner.username if owner else None,
                "phone": owner.phone if owner else None,
            },
            "start_date": rental.start_date,
            "end_date": rental.end_date,
            "total_price": rental.total_price,
            "deposit_amount": rental.deposit_amount,
            #"status": rental.status.value, # строка?
            "status": rental.status, # RentalStatus.REQUESTED и т.д. - enum?
            "status_display": rental.status.value.replace("_", " ").capitalize(),
            "created_at": rental.created_at,
            "updated_at": rental.updated_at,
            "current_user_role": role,
            "owner_handover_confirmed": rental.owner_handover_confirmed,
            "renter_receive_confirmed": rental.renter_receive_confirmed,
        }

        return details


    # ==================   STATUS MANAGEMENT — ядро бизнес-логики   ===============================
    """Важно: сервис возвращает None и кидает исключение — это удобно. 
    Хендлер ловит и показывает человеку текст."""

    #! Переход: REQUESTED → CONFIRMED
    async def confirm_requested(self, *, rental_id: int, actor_id: int) -> bool: # -> None:
        """Подтвердить REQUESTED → CONFIRMED может только владелец"""
        ok = await self.rental_repo.update_status_if_allowed(
            rental_id=rental_id,
            new_status=RentalStatus.CONFIRMED,
            expected_status=RentalStatus.REQUESTED,
            actor_user_id=actor_id,
            actor_field="owner_id",
        )
        """
        ok=True  →  статус реально сменился в базе (1 строка обновлена)
        ok=False →  ничего не изменилось (0 строк обновлено), значит:
                    либо статус уже не REQUESTED,        
                    либо rental_id не существует,        
                    либо owner_id не совпал (не тот актёр).        
        И сервис превращает это в понятную ошибку.
        """
        #if not ok:
        #    raise ValueError("Нельзя подтвердить: статус изменился или недостаточно прав")
        return ok

    #! REQUESTED → REJECTED_BY_OWNER
    async def reject_requested_by_owner(self, *, rental_id: int, owner_id: int) -> bool: # -> None:
        """REQUESTED → REJECTED (владелец отклоняет)"""
        ok = await self.rental_repo.update_status_if_allowed(
            rental_id=rental_id,
            new_status=RentalStatus.REJECTED_BY_OWNER,
            expected_status=RentalStatus.REQUESTED,
            actor_user_id=owner_id,
            actor_field="owner_id",
        )
        #if not ok:
        #    raise ValueError("Нельзя отклонить запрос аренды")
        return ok

    # REQUESTED → REJECTED_BY_RENTER
    async def reject_requested_by_renter(self, *, rental_id: int, renter_id: int) -> bool: # -> None:
        """REQUESTED → CANCELLED_BY_RENTER (арендатор отклоняет)"""
        ok = await self.rental_repo.update_status_if_allowed(
            rental_id=rental_id,
            new_status=RentalStatus.REJECTED_BY_RENTER,
            expected_status=RentalStatus.REQUESTED,
            actor_user_id=renter_id,
            actor_field="renter_id",
        )
        #if not ok:
        #    raise ValueError("Нельзя отменить: статус изменился или недостаточно прав")
        return ok

    # CONFIRMED → CANCELLED_CONFIRMED_BY_OWNER
    async def cancel_confirmed_by_owner(self, *, rental_id: int, owner_id: int) -> bool: # -> None:
        """Владелец отклоняет утвержденную аренду"""
        ok = await self.rental_repo.update_status_if_allowed(
            rental_id=rental_id,
            new_status=RentalStatus.CANCELLED_CONFIRMED_BY_OWNER,
            expected_status=RentalStatus.CONFIRMED,
            actor_user_id=owner_id,
            actor_field="owner_id",
        )
        return ok

    # CONFIRMED → CANCELLED_CONFIRMED_BY_RENTER
    async def cancel_confirmed_by_renter(self, *, rental_id: int, renter_id: int) -> bool: # -> None:
        """Арендатор отклоняет утвержденную аренду"""
        ok = await self.rental_repo.update_status_if_allowed(
            rental_id=rental_id,
            new_status=RentalStatus.CANCELLED_CONFIRMED_BY_RENTER,
            expected_status=RentalStatus.CONFIRMED,
            actor_user_id=renter_id,
            actor_field="renter_id",
        )
        return ok


    # CONFIRMED → ACTIVE
    async def start_rental(self, *, rental_id: int, owner_id: int) -> bool: # -> None:
        """начало аренды [в будущем автоматически по дате]"""
        ok = await self.rental_repo.update_status_if_allowed(
            rental_id=rental_id,
            new_status=RentalStatus.ACTIVE,
            expected_status=RentalStatus.CONFIRMED,
            actor_user_id=owner_id,
            actor_field="owner_id",
        )
        #if not ok:
        #    raise ValueError("Нельзя начать аренду")
        return ok

    async def confirm_handover_by_owner(self, *, rental_id: int, owner_id: int) -> bool:
        """Владелец нажал 'Передал вещь'"""
        ok = await self.rental_repo.owner_confirm_handover(rental_id=rental_id, owner_id=owner_id)
        if not ok:
            return False
        # если арендатор уже подтвердил получение — активируем
        await self.rental_repo.activate_if_ready(rental_id=rental_id)
        return True

        # if ok:
        #    # если владелец уже подтвердил передачу — активируем
        #    await self.rental_repo.activate_if_ready(rental_id=rental_id)
        #    return ok

    async def confirm_receive_by_renter(self, *, rental_id: int, renter_id: int) -> bool:
        """Арендатор нажал 'Получил вещь'"""
        ok = await self.rental_repo.renter_confirm_receive(rental_id=rental_id, renter_id=renter_id)
        if not ok:
            return False
        # если владелец уже подтвердил передачу — активируем
        await self.rental_repo.activate_if_ready(rental_id=rental_id)
        return True


    #! ACTIVE → COMPLETED
    async def complete_active(self, *, rental_id: int, owner_id: int) -> bool: #-> None:
        """Владелец завершает аренду = возврат вещи (можно сделать и арендатором)"""
        ok = await self.rental_repo.update_status_if_allowed(
            rental_id=rental_id,
            new_status=RentalStatus.COMPLETED,
            expected_status=RentalStatus.ACTIVE,
            actor_user_id=owner_id,
            actor_field="owner_id",
        )
        #if not ok:
        #    raise ValueError("Нельзя завершить аренду")
        return ok

    #! ACTIVE → CANCELLED_BY_OWNER
    async def cancel_active_by_owner(self, *, rental_id: int, owner_id: int) -> bool: # -> None:
        """ACTIVE → CANCELLED_BY_OWNER (отмена активной аренды владельцем)"""
        ok = await self.rental_repo.update_status_if_allowed(
            rental_id=rental_id,
            new_status=RentalStatus.CANCELLED_BY_OWNER,
            expected_status=RentalStatus.ACTIVE,
            actor_user_id=owner_id,
            actor_field="owner_id",
        )
        #if not ok:
        #    raise ValueError("Нельзя отменить активную аренду владельцем")
        return ok

    #! ACTIVE → CANCELLED_BY_RENTER
    async def cancel_active_by_renter(self, *, rental_id: int, renter_id: int) -> bool: # -> None:
        """ACTIVE → CANCELLED_BY_RENTER (отмена активной аренды арендатором)"""
        ok = await self.rental_repo.update_status_if_allowed(
            rental_id=rental_id,
            new_status=RentalStatus.CANCELLED_BY_RENTER,
            expected_status=RentalStatus.ACTIVE,
            actor_user_id=renter_id,
            actor_field="renter_id",
        )
        #if not ok:
        #    raise ValueError("Нельзя отменить активную аренду арендатором")
        return ok

    # ACTIVE → DISPUTED
    async def open_dispute(self, *, rental_id: int, actor_id: int) -> bool: #-> None:
        """ Открыть спор: может owner или renter"""

        #allowed_from = (RentalStatus.CONFIRMED, RentalStatus.ACTIVE)  # при желании добавь COMPLETED

        #for expected in allowed_from:
        ok = await self.rental_repo.update_status_if_participant(
            rental_id=rental_id,
            new_status=RentalStatus.DISPUTED,
            expected_status=RentalStatus.ACTIVE,  # expected
            actor_user_id=actor_id,
        )
        #if not ok:
        #    raise ValueError("Нельзя открыть спор: нет прав или статус уже изменился")
        return ok



    # ==================   ADMIN MANAGEMENT — админка  ===============================

    async def get_open_rental_for_item(self, item_id: int): # -> Optional[RentalOut]
        """Возвращает первую открытую аренду для item_id или None"""
        rentals = await self.rental_repo.get_last_open_by_item_id(item_id)
        for r in rentals:
            if is_open_status(r.status):
                return r # RentalOut.model_validate(r)
        return None

    # Для доменной проверки (будет ниже) лучше работать с моделью БД Rental, без Pydantic-валидации (RentalOut).
    # Это быстрее и проще, и меньше шансов на “почему end_date не того типа”.

    async def ensure_item_available(self, item_id: int) -> None:
        """Доменная гарантия: item нельзя арендовать, если есть открытая аренда"""
        r = await self.get_open_rental_for_item(item_id)
        if not r:
            return

        status_val = getattr(r.status, "value", str(r.status))
        end_date = getattr(r, "end_date", None)

        raise ItemNotAvailable(
            item_id=item_id,
            rental_id=r.id,
            status=str(status_val),
            end_date=str(end_date) if end_date else None,
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

    def confirm_rental(self, rental_id: int, user_id: int) -> bool:
        ""Владелец подтверждает запрос на аренду → CONFIRMED (из REQUESTED)""
        return self._change_status(
            rental_id=rental_id,
            user_id=user_id,
            allowed_roles=["owner"],
            allowed_current_statuses=[RentalStatus.REQUESTED],
            new_status=RentalStatus.CONFIRMED,
            action_name="confirm_rental",
            notify_recipient_role="renter",
            notify_message_template="✅ Ваш запрос на аренду товара {item_name} подтвержден владельцем.",
            notify_button_text="🔍 Посмотреть сделку",
        )

    def reject_rental(self, rental_id: int, user_id: int) -> bool:
        ""Владелец отклоняет запрос → REJECTED (из REQUESTED)""
        return self._change_status(
            rental_id=rental_id,
            user_id=user_id,
            allowed_roles=["owner"],
            allowed_current_statuses=[RentalStatus.REQUESTED],
            new_status=RentalStatus.REJECTED,
            action_name="reject_rental",
            notify_recipient_role="renter",
            notify_message_template="🚫 Ваш запрос на аренду товара {item_name} отклонен владельцем.",
            notify_button_text="🔍 Посмотреть детали",
        )

    def start_rental(self, rental_id: int, user_id: int) -> bool:
        ""Владелец запускает аренду (передал вещь) → ACTIVE (из CONFIRMED)""
        return self._change_status(
            rental_id=rental_id,
            user_id=user_id,
            allowed_roles=["owner"],
            allowed_current_statuses=[RentalStatus.CONFIRMED],
            new_status=RentalStatus.ACTIVE,
            action_name="start_rental",
            notify_recipient_role="renter",
            notify_message_template="▶️ Аренда товара {item_name} началась.",
            notify_button_text="🔍 Посмотреть детали",
        )

    def complete_rental(self, rental_id: int, user_id: int) -> bool:
        ""Владелец завершает аренду (вещь возвращена) → COMPLETED (из ACTIVE)""
        return self._change_status(
            rental_id=rental_id,
            user_id=user_id,
            allowed_roles=["owner"],
            allowed_current_statuses=[RentalStatus.ACTIVE],
            new_status=RentalStatus.COMPLETED,
            action_name="complete_rental",
            notify_recipient_role="renter",
            notify_message_template="🏁 Аренда товара {item_name} завершена. Спасибо за использование сервиса!",
            notify_button_text="⭐ Оставить отзыв",
            notify_button_callback_action=f"rental_action:review:{rental_id}",
        )

    def cancel_rental_request(self, rental_id: int, user_id: int) -> bool:
        ""Арендатор отменяет свой запрос → CANCELLED (из REQUESTED)""
        return self._change_status(
            rental_id=rental_id,
            user_id=user_id,
            allowed_roles=["renter"],
            allowed_current_statuses=[RentalStatus.REQUESTED],
            new_status=RentalStatus.CANCELLED,
            action_name="cancel_rental_request",
            notify_recipient_role="owner",
            notify_message_template="⚠️ Арендатор отменил запрос на аренду вашего товара {item_name}.",
            notify_button_text="🔍 Посмотреть детали",
        )

    def cancel_confirmed_rental(self, rental_id: int, user_id: int) -> bool:
        ""Отмена подтверждённой, но не начатой аренды любой стороной → CANCELLED (из CONFIRMED)""
        # Инициатор важен только для текста уведомления — статус в модели единый (CANCELLED)
        initiator = "арендатор"  # подставим корректно ниже
        rental = self.repo.get_by_id(rental_id)
        if rental:
            initiator = "владелец" if rental.owner_id == user_id else "арендатор"

        return self._change_status(
            rental_id=rental_id,
            user_id=user_id,
            allowed_roles=["renter", "owner"],
            allowed_current_statuses=[RentalStatus.CONFIRMED],
            new_status=RentalStatus.CANCELLED,
            action_name="cancel_confirmed_rental",
            notify_recipient_role="other",
            notify_message_template=f"🚫 Сделка по аренде товара {{item_name}} была отменена {initiator}.",
            notify_button_text="🔍 Посмотреть детали",
        )

    def start_dispute(self, rental_id: int, user_id: int) -> bool:
        ""Открыть спор → DISPUTED (обычно из ACTIVE/COMPLETED)""
        return self._change_status(
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
