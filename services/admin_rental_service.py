import logging
from typing import Optional
from decimal import Decimal
from datetime import datetime, timezone


from db.repositories.rental import RentalRepository
from services.admin_service import AdminActionService
from services.rental_service import RentalService

from schemas.rental import RentalOut, RentalAdminDetailsOut, RentalUpdate, RentalStatusUpdate
from schemas.item import ItemOut
from schemas.user import UserOut
from status.admin_status import AdminEntityType, admin_action_for_rental_status
from status.rental_status import RentalStatus, can_transition, status_timestamp_fields
from utils.errors import NotFoundError, ConflictError, ValidationError

logger = logging.getLogger(__name__)

_PAGE_SIZE = 8

class AdminRentalService:
    """Админский сервис для просмотра и обработки заявок клиентов на аренду."""

    def __init__(self, repo: RentalRepository, admin_service: AdminActionService) -> None:
        self.repo = repo
        self.admin_service = admin_service

    # ────────────────────────────────────────── DTO helpers ──────────────────────────────────────────────────────────
    @staticmethod
    def _to_rental_out(rental) -> RentalOut:
        return RentalOut.model_validate(rental)

    @classmethod
    def _to_admin_details(cls, rental) -> RentalAdminDetailsOut:
        return RentalAdminDetailsOut(
            rental=RentalOut.model_validate(rental),
            item=ItemOut.model_validate(rental.item),
            user=UserOut.model_validate(rental.user),
        )

    @classmethod
    def _to_admin_details_list(cls, rentals) -> list[RentalAdminDetailsOut]:
        return [cls._to_admin_details(rental) for rental in rentals]
        # Замена:
        # rows: list[RentalAdminDetailsOut] = []
        # for r in rentals:
        #     rows.append(cls._to_admin_details(r))

    # ─────────────────────────────────────── Business validation ─────────────────────────────────────────────────────
    @staticmethod
    def _validate_non_empty_text(value: str, field_name: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValidationError(f"{field_name} не может быть пустым")
        return normalized

    @staticmethod
    def _ensure_status_transition(old_status: RentalStatus, new_status: RentalStatus, *, strict: bool) -> bool:
        if can_transition(old_status, new_status):
            return True

        if strict:
            raise ConflictError(f"Нельзя изменить статус заявки: {old_status.value} -> {new_status.value}")
        return False

    @staticmethod
    def _build_status_update(
            *,
            status: RentalStatus,
            changed_at: datetime | None = None,
            manager_comment: str | None = None,
            reject_reason: str | None = None,
            cancel_reason: str | None = None,
    ) -> RentalStatusUpdate:
        """Собрать доменный patch статуса заявки, включая статусные timestamp-поля."""
        actual_changed_at = changed_at or datetime.now(timezone.utc)
        update_data = RentalStatusUpdate(status=status)

        if manager_comment is not None:
            update_data.manager_comment = manager_comment
        if reject_reason is not None:
            update_data.reject_reason = reject_reason
        if cancel_reason is not None:
            update_data.cancel_reason = cancel_reason

        for field_name in status_timestamp_fields(status):
            setattr(update_data, field_name, actual_changed_at)

        return update_data

    # ?
    @staticmethod
    def _validate_required_reason(status: RentalStatus, comment: Optional[str]) -> None:
        """Проверить, что для отрицательных решений указана причина."""
        if status == RentalStatus.REJECTED and not comment:
            raise ValidationError("Укажите причину отклонения заявки")

        if status == RentalStatus.CANCELLED_BY_ADMIN and not comment:
            raise ValidationError("Укажите причину отмены заявки")

    # ────────────────────────────────────────── Read methods ──────────────────────────────────────────────────────────
    async def list_recent_rentals(self, page: int) -> tuple[list[RentalAdminDetailsOut], bool]:
        """Админ-экран: последние заявки клиентов."""
        safe_page = max(1, page)
        limit = _PAGE_SIZE
        offset = (safe_page - 1) * limit

        rentals = await self.repo.list_recent_with_details_for_admins(limit=limit + 1, offset=offset)
        has_next = len(rentals) > limit

        return self._to_admin_details_list(rentals[:limit]), has_next # rows, has_next

    async def list_rentals_by_status(self, status: RentalStatus, page: int) -> tuple[list[RentalAdminDetailsOut], bool]:
        """Админ-экран: заявки клиентов с указанным статусом."""
        safe_page = max(1, page)
        limit = _PAGE_SIZE
        offset = (safe_page - 1) * limit

        rentals = await self.repo.list_by_status_with_details_for_admins(status, limit=limit + 1, offset=offset)
        has_next = len(rentals) > limit

        return self._to_admin_details_list(rentals[:limit]), has_next

    async def get_details(self, rental_id: int, *, strict: bool = False) -> Optional[RentalAdminDetailsOut]:
        """Вернуть подробную информацию о заявке для администратора/менеджера."""
        rental = await self.repo.get_details_by_id(rental_id)
        if not rental:
            if strict:
                raise NotFoundError(f"Заявка не найдена: id={rental_id}")
            return None

        return self._to_admin_details(rental)

    # ────────────────────────────────────── Admin rental actions ──────────────────────────────────────────────────────
    # нужно доработка и осмысление функции!
    async def change_status(
            self,
            *,
            rental_id: int,
            admin_tg_id: int,
            new_status: RentalStatus,
            manager_comment: Optional[str] = None,
            reject_reason: Optional[str] = None,
            cancel_reason: Optional[str] = None,
            strict: bool = False
    ) -> Optional[RentalOut]:
        """Изменить статус заявки сотрудником с проверкой разрешённого перехода."""

        rental = await self.repo.get_by_id(rental_id)
        if not rental:
            if strict:
                raise NotFoundError(f"Заявка не найдена: id={rental_id}")
            return None

        old_status = rental.status
        if old_status == new_status:
            return self._to_rental_out(rental)

        # Проверяем, разрешён ли переход
        if not self._ensure_status_transition(old_status, new_status, strict=strict):
            return None

        normalized_comment = manager_comment.strip() if manager_comment else None
        normalized_reject_reason = reject_reason.strip() if reject_reason else None
        normalized_cancel_reason = cancel_reason.strip() if cancel_reason else None
        reason_for_status = {
            RentalStatus.REJECTED: normalized_reject_reason,
            RentalStatus.CANCELLED_BY_ADMIN: normalized_cancel_reason,
        }.get(new_status)
        self._validate_required_reason(new_status, reason_for_status) # нужно доосмыслить!

        update_data = self._build_status_update(
            status=new_status,
            manager_comment=normalized_comment,
            reject_reason=normalized_reject_reason,
            cancel_reason=normalized_cancel_reason,
        )

        updated = await self.repo.apply_update_if_current_status(
            rental_id=rental_id,
            expected_status=old_status,
            update_data=update_data,
        )

        if not updated:
            if strict:
                raise ConflictError("Не удалось обновить статус заявки")
            return None

        updated_rental = await self.repo.get_by_id(rental_id)
        if not updated_rental:
            if strict:
                raise NotFoundError(f"Заявка не найдена после обновления: id={rental_id}")
            return None

        # Пишем audit-log
        await self.admin_service.log_action(
            admin_tg_id=admin_tg_id,
            action_type=admin_action_for_rental_status(new_status),
            entity_type=AdminEntityType.RENTAL,
            entity_id=rental_id,
            note=f"Сотрудник изменил статус заявки #{rental_id}",
            payload={
                "from_status": old_status.value,
                "to_status": new_status.value,
                "manager_comment": normalized_comment,
                "reject_reason": normalized_reject_reason,
                "cancel_reason": normalized_cancel_reason,
            },
        )

        logger.info("Статус заявки изменён сотрудником: id=%s %s->%s", rental_id, old_status.value, new_status.value)
        return self._to_rental_out(updated_rental)

    """  
    Лучше:
        manager_comment — обычный внутренний комментарий менеджера
        reject_reason — причина отклонения
        cancel_reason — причина отмены
    
    Полноценная логика была бы такой:
    
    1. В модели Rental отдельные поля:
       reject_reason
       cancel_reason
        
    2. В schemas:
       reject_reason / cancel_reason
    
    3. В service:
       reject_rental(reason)
       admin_cancel_rental(reason)
    
    4. В notifications:
       клиент получает понятную причину
    
    5. В audit:
       причина пишется отдельно в payload
    """

    # Переход REQUESTED → IN_PROGRESS.
    async def take_in_progress(self, *, rental_id: int, admin_tg_id: int, strict: bool = False) -> Optional[RentalOut]:
        """Взять заявку в работу."""
        return await self.change_status(rental_id=rental_id, admin_tg_id=admin_tg_id,
                                        new_status=RentalStatus.IN_PROGRESS, strict=strict)

    # Переход IN_PROGRESS / REQUESTED → CONFIRMED
    async def confirm_rental(
            self,
            *,
            rental_id: int,
            admin_tg_id: int,
            manager_comment: Optional[str] = None,
            strict: bool = False,
    ) -> Optional[RentalOut]:
        """Подтвердить заявку клиента."""
        return await self.change_status(rental_id=rental_id, admin_tg_id=admin_tg_id, new_status=RentalStatus.CONFIRMED,
                                        manager_comment=manager_comment, strict=strict)

    # Переход REQUESTED/IN_PROGRESS → REJECTED (заявку не приняли в работу / не одобрили)
    async def reject_rental(self, *, rental_id: int, admin_tg_id: int, reason: str, strict: bool = False) -> Optional[RentalOut]:
        """Отклонить заявку клиента с обязательной причиной."""
        return await self.change_status(rental_id=rental_id, admin_tg_id=admin_tg_id, new_status=RentalStatus.REJECTED,
                                        reject_reason=reason, strict=strict)

    # Переход CONFIRMED → CANCELLED_BY_ADMIN (заявку уже приняли/подтвердили, но потом компания её отменила)
    async def admin_cancel_rental(self, *, rental_id: int, admin_tg_id: int, reason: str, strict: bool = False) -> Optional[RentalOut]:
        """Отменить открытую заявку сотрудником компании с обязательной причиной."""
        return await self.change_status(rental_id=rental_id, admin_tg_id=admin_tg_id,
                                        new_status=RentalStatus.CANCELLED_BY_ADMIN, cancel_reason=reason,
                                        strict=strict)

    # Переход (менеджер закрывает заявку как завершённую [товар выдан/возвращён]): ACTIVE / ISSUED → COMPLETED
    async def complete_rental(
            self,
            *,
            rental_id: int,
            admin_tg_id: int,
            manager_comment: Optional[str] = None,
            strict: bool = False,
    ) -> Optional[RentalOut]:
        """Завершить заявку."""
        return await self.change_status(rental_id=rental_id, admin_tg_id=admin_tg_id, new_status=RentalStatus.COMPLETED,
                                        manager_comment=manager_comment, strict=strict)

    async def update_manager_comment( self, *, rental_id: int, admin_tg_id: int, manager_comment: str, strict: bool = False,
    ) -> Optional[RentalOut]:
        """Обновить внутренний комментарий менеджера без смены статуса."""
        normalized_comment = self._validate_non_empty_text(manager_comment, "Комментарий менеджера")
        updated = await self.repo.update(rental_id, RentalUpdate(manager_comment=normalized_comment))
        if not updated:
            if strict:
                raise NotFoundError(f"Заявка не найдена: id={rental_id}")
            return None

        await self.admin_service.log_action(
            admin_tg_id=admin_tg_id,
            action_type=admin_action_for_rental_status(updated.status),
            entity_type=AdminEntityType.RENTAL,
            entity_id=rental_id,
            note=f"Сотрудник обновил комментарий менеджера заявки #{rental_id}",
            payload={"manager_comment": normalized_comment},
        )
        return self._to_rental_out(updated)

    # На будущее:
        # Переход (начало аренды [менеджер выдал товар клиенту]): CONFIRMED → ACTIVE / ISSUED - start_rental()
        # Переход (Открыть спор: может owner или renter): ACTIVE → DISPUTED - open_dispute()


    # Проверь
    async def update_manager_pricing(
            self,
            *,
            rental_id: int,
            rental_days: int,
            delivery_price: Optional[Decimal] = None,
            final_price: Optional[Decimal] = None,
            strict: bool = False,
    ) -> Optional[RentalOut]:
        """Сохранить менеджерский расчёт после звонка клиенту.

        Пользователь при создании заявки сообщает только ориентировочный период.
        Менеджер уточняет точное количество дней, сервис выбирает тариф,
        пересчитывает предварительную стоимость и сохраняет доставку/final price, если они уже известны.
        """
        rental = await self.repo.get_details_by_id(rental_id)
        if not rental:
            if strict:
                raise NotFoundError(f"Заявка не найдена: id={rental_id}")
            return None

        tier = RentalService.select_price_tier(rental.item.price_tiers, rental_days)
        price_per_day_snapshot = Decimal(tier.price_per_day).quantize(Decimal("0.01"))
        total_price = RentalService.calculate_total_price(rental_days, rental.quantity, price_per_day_snapshot)
        rental_period_text = rental.rental_period_text or RentalService.build_price_tier_label(tier)

        updated = await self.repo.update(
            rental_id,
            RentalUpdate(
                rental_days=rental_days,
                rental_period_text=rental_period_text,
                price_per_day_snapshot=price_per_day_snapshot,
                total_price=total_price,
                delivery_price=delivery_price,
                final_price=final_price,
            ),
        )
        if not updated:
            if strict:
                raise NotFoundError(f"Заявка не найдена: id={rental_id}")
            return None

        return self._to_rental_out(updated)


    # ?
    @staticmethod
    def admin_rental_actions_for_status(status: RentalStatus) -> tuple[str, ...]:
        """Вернуть допустимые admin UI-actions для текущего статуса заявки."""
        actions: list[str] = []
        if can_transition(status, RentalStatus.IN_PROGRESS):
            actions.append("progress")
        if can_transition(status, RentalStatus.CONFIRMED):
            actions.append("confirm")
        if can_transition(status, RentalStatus.REJECTED):
            actions.append("reject")
        if can_transition(status, RentalStatus.CANCELLED_BY_ADMIN):
            actions.append("cancel")
        if can_transition(status, RentalStatus.COMPLETED):
            actions.append("complete")
        return tuple(actions)


    # ─────────────────────────────── Пока не используемые ─────────────────────────────────────────────────────────────
    async def admin_set_status(
            self,
            *,
            rental_id: int,
            admin_tg_id: int,
            new_status: RentalStatus,
            manager_comment: Optional[str] = None,
            strict: bool = False
    ) -> Optional[RentalOut]:
        """Публичный wrapper для смены статуса заявки сотрудником."""
        return await self.change_status(
            rental_id=rental_id,
            admin_tg_id=admin_tg_id,
            new_status=new_status,
            manager_comment=manager_comment,
            strict=strict,
        )