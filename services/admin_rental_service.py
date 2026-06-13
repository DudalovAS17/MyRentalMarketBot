import logging
from typing import Optional
from datetime import datetime, timezone

from db.repositories.rental import RentalRepository
from services.admin_service import AdminActionService

from schemas.rental import RentalUpdate, RentalOut, RentalAdminDetailsOut
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

    @staticmethod
    def _build_status_update(
        *,
        status: RentalStatus,
        changed_at: datetime,
        manager_comment: Optional[str] = None,
    ) -> RentalUpdate:
        update_data = RentalUpdate(
            status=status,
            manager_comment=manager_comment
        )
        for field_name in status_timestamp_fields(status):
            setattr(update_data, field_name, changed_at)
        return update_data

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
    async def admin_set_status(
            self,
            *,
            rental_id: int,
            admin_tg_id: int,
            new_status: RentalStatus,
            manager_comment: Optional[str] = None,
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
        self._validate_required_reason(new_status, normalized_comment) # нужно доосмыслить!

        # Собираем RentalUpdate
        update_data = self._build_status_update(
            status=new_status,
            changed_at=datetime.now(timezone.utc),
            manager_comment=normalized_comment,
        )

        updated = await self.repo.update(rental_id, update_data)
        if not updated:
            if strict:
                raise ConflictError("Не удалось обновить статус заявки")
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
            },
        )

        logger.info("Статус заявки изменён сотрудником: id=%s %s->%s", rental_id, old_status.value, new_status.value)
        return self._to_rental_out(updated)

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
        return await self.admin_set_status(
            rental_id=rental_id,
            admin_tg_id=admin_tg_id,
            new_status=RentalStatus.IN_PROGRESS,
            strict=strict,
        )

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
        return await self.admin_set_status(
            rental_id=rental_id,
            admin_tg_id=admin_tg_id,
            new_status=RentalStatus.CONFIRMED,
            manager_comment=manager_comment,
            strict=strict,
        )

    # Переход REQUESTED/IN_PROGRESS → REJECTED (заявку не приняли в работу / не одобрили)
    async def reject_rental(self, *, rental_id: int, admin_tg_id: int, reason: str, strict: bool = False) -> Optional[RentalOut]:
        """Отклонить заявку клиента с обязательной причиной."""
        return await self.admin_set_status(
            rental_id=rental_id,
            admin_tg_id=admin_tg_id,
            new_status=RentalStatus.REJECTED,
            manager_comment=reason,
            strict=strict,
        )

    # Переход CONFIRMED → CANCELLED_BY_ADMIN (заявку уже приняли/подтвердили, но потом компания её отменила)
    async def admin_cancel_rental(self, *, rental_id: int, admin_tg_id: int, reason: str, strict: bool = False) -> Optional[RentalOut]:
        """Отменить открытую заявку сотрудником компании с обязательной причиной."""
        return await self.admin_set_status(
            rental_id=rental_id,
            admin_tg_id=admin_tg_id,
            new_status=RentalStatus.CANCELLED_BY_ADMIN,
            manager_comment=reason,
            strict=strict,
        )

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
        return await self.admin_set_status(
            rental_id=rental_id,
            admin_tg_id=admin_tg_id,
            new_status=RentalStatus.COMPLETED,
            manager_comment=manager_comment,
            strict=strict,
        )

    # На будущее:
        # Переход (начало аренды [менеджер выдал товар клиенту]): CONFIRMED → ACTIVE / ISSUED - start_rental()
        # Переход (Открыть спор: может owner или renter): ACTIVE → DISPUTED - open_dispute()

"""
    В нашем новом домене компания сама управляет выдачей товара. Если когда-нибудь понадобится выдача/возврат:
        AdminRentalService.mark_item_issued()
        AdminRentalService.mark_item_returned()
    
    это аналог из rental_service (удалены)
        confirm_handover_by_owner - Владелец нажал 'Передал вещь' (CONFIRMED)
        confirm_receive_by_renter - Арендатор нажал 'Получил вещь' (CONFIRMED)
"""