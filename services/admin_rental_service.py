import logging
from typing import Optional

from db.repositories.rental import RentalRepository
from services.admin_service import AdminActionService

from schemas.rental import RentalUpdate, RentalOut, RentalAdminDetailsOut
from schemas.item import ItemOut
from schemas.user import UserOut
from status.admin_status import AdminActionType, AdminEntityType, CANCEL_STATUS_MAP, ALLOWED_TARGETS
from status.rental_status import TERMINAL_STATUSES, RentalStatus
from utils.errors import NotFoundError, ConflictError

logger = logging.getLogger(__name__)

_PAGE_SIZE = 8

class AdminRentalService:
    """Админский сервис для просмотра сделок и властного вмешательства в их жизненный цикл"""

    def __init__(self, rental_repo: RentalRepository, admin_service: AdminActionService) -> None:
        self.rental_repo = rental_repo
        self.admin_service = admin_service

    # ────────────────────────────────────────── Read methods ──────────────────────────────────────────────────────────
    async def list_recent_rentals(self, page: int) -> tuple[list[RentalAdminDetailsOut], bool]:
        """Админ-экран: последние сделки"""
        safe_page = max(1, page)
        limit = _PAGE_SIZE
        offset = (safe_page - 1) * limit

        rentals = await self.rental_repo.list_recent_with_details_for_admins(limit=limit + 1, offset=offset)

        has_next = len(rentals) > limit
        rentals = rentals[:limit]

        rows: list[RentalAdminDetailsOut] = []
        for r in rentals:
            rows.append(RentalAdminDetailsOut(
                rental=RentalOut.model_validate(r),
                item=ItemOut.model_validate(r.item),
                owner=UserOut.model_validate(r.owner),
                renter=UserOut.model_validate(r.renter)
            ))

        return rows, has_next

    async def get_details(self, rental_id: int, *, strict: bool = False) -> Optional[RentalAdminDetailsOut]:
        """Вернуть подробную информацию о сделке для администратора"""
        r = await self.rental_repo.get_details_by_id(rental_id)
        if not r:
            if strict:
                raise NotFoundError(f"Сделка не найдена: id={rental_id}")
            return None

        return RentalAdminDetailsOut(
            rental=RentalOut.model_validate(r),
            item=ItemOut.model_validate(r.item),
            owner=UserOut.model_validate(r.owner),
            renter=UserOut.model_validate(r.renter),
        )

    # ────────────────────────────────────── admin override admin_actions ────────────────────────────────────────────────────
    async def admin_cancel_rental(self, rental_id: int, admin_tg_id: int, reason: str, *, strict: bool = False) -> bool:
        """Принудительно отменить сделку администратором"""

        rental = await self.rental_repo.get_by_id(rental_id)
        if not rental:
            if strict:
                raise NotFoundError(f"Сделка не найдена: id={rental_id}")
            return False

        terminal_block = TERMINAL_STATUSES
        if rental.status in terminal_block:
            if strict:
                raise ConflictError("Сделку нельзя отменить: она в терминальном статусе")
            return False

        status_map = CANCEL_STATUS_MAP
        new_status = status_map.get(rental.status)
        if new_status is None:
            if strict:
                raise ConflictError("Сделку нельзя отменить из текущего статуса")
            return False

        updated = await self.rental_repo.update(rental_id, RentalUpdate(status=new_status)) # RentalStatus.CANCELLED_BY_OWNER
        if not updated:
            if strict:
                raise ConflictError("Не удалось отменить сделку (возможно, уже изменена)")
            return False

        await self.admin_service.log_action(
            admin_tg_id=admin_tg_id,
            action_type=AdminActionType.ADMIN_CANCEL_RENTAL,
            entity_type=AdminEntityType.RENTAL,
            entity_id=rental_id,
            note=f"Админ отменил сделку #{rental_id}",
            payload={
                "reason": reason,
                "from_status": rental.status.value,
                "to_status": new_status.value
            }
        )

        logger.info("Админ отменил сделку id=%s from=%s to=%s", rental_id, rental.status.value, new_status.value)
        return True

    async def admin_resolve_dispute(
            self,
            rental_id: int,
            admin_tg_id: int,
            resolution: str,
            target_status: RentalStatus,
            strict: bool = False
    ) -> bool:
        """Закрыть спор по сделке и перевести её в допустимый итоговый статус"""

        rental = await self.rental_repo.get_by_id(rental_id)
        if not rental:
            if strict:
                raise NotFoundError(f"Сделка не найдена: id={rental_id}")
            return False

        # закрываем спор только если он открыт
        if rental.status != RentalStatus.DISPUTED:
            if strict:
                raise ConflictError("Спор можно закрыть только если статус DISPUTED")
            return False

        allowed_targets = ALLOWED_TARGETS
        if target_status not in allowed_targets:
            if strict:
                raise ConflictError("Недопустимый исход спора")
            return False

        updated = await self.rental_repo.update(rental_id, RentalUpdate(status=target_status))
        if not updated:
            if strict:
                raise ConflictError("Не удалось обновить статус сделки")
            return False

        await self.admin_service.log_action(
            admin_tg_id=admin_tg_id,
            action_type=AdminActionType.RESOLVE_DISPUTE,
            entity_type=AdminEntityType.RENTAL,
            entity_id=rental_id,
            note=f"Разрешен спор для сделки #{rental_id}",
            payload={
                "resolution": resolution,
                "from_status": rental.status.value,
                "to_status": target_status.value
            },
        )

        logger.info("Админ разрешил спор сделки id=%s to=%s", rental_id, target_status.value)
        return True