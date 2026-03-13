import logging
from typing import Optional, List

from db.models.rental import RentalStatus
from db.repositories.rental import RentalRepository
from services.admin_service import AdminActionService
from schemas.rental import RentalUpdate, RentalOut, RentalAdminDetailsOut
from schemas.item import ItemOut
from schemas.user import UserOut
from status.admin_status import AdminActionType, AdminEntityType
from utils.errors import NotFoundError, ConflictError

logger = logging.getLogger(__name__)

class AdminRentalService:
    """
    Админский сервис по сделкам:
    - листинг последних
    - просмотр по id
    - cancel / resolve_dispute
    """

    PAGE_SIZE = 8

    # Имеем ли мы право вмешиваться сейчас.
    # Множество состояний, в которых сделка уже завершена по смыслу.
    _TERMINAL_STATUSES_ = {
        RentalStatus.COMPLETED,
        RentalStatus.REJECTED_BY_OWNER,
        RentalStatus.REJECTED_BY_RENTER,
        RentalStatus.CANCELLED_BY_OWNER,
        RentalStatus.CANCELLED_BY_RENTER,
        RentalStatus.CANCELLED_CONFIRMED_BY_OWNER,
        RentalStatus.CANCELLED_CONFIRMED_BY_RENTER,
    }

    # Что именно означает “отмена” на этом этапе
    # (пока так: не добавляли статусы "Админ отменил", а используем эти, но в audit будет видно, что админ отменил)
    _CANCEL_STATUS_MAP_ = {
        RentalStatus.REQUESTED: RentalStatus.REJECTED_BY_OWNER,  # REQUESTED → REJECTED_BY_OWNER
        RentalStatus.CONFIRMED: RentalStatus.CANCELLED_CONFIRMED_BY_OWNER,
        RentalStatus.ACTIVE: RentalStatus.CANCELLED_BY_OWNER,
        RentalStatus.DISPUTED: RentalStatus.CANCELLED_BY_OWNER,
    }

    # допустимые исходы для "закрытия спора"
    _ALLOWED_TARGETS_ = {RentalStatus.ACTIVE, RentalStatus.COMPLETED, RentalStatus.CONFIRMED}

    def __init__(
        self,
        rental_repo: RentalRepository,
        admin_service: AdminActionService,
    ):
        self.rental_repo = rental_repo
        self.admin_service = admin_service

    async def list_recent_rentals(self, page: int) -> tuple[List[RentalAdminDetailsOut], bool]:
        """“Админ-экран: последние сделки
        limit N - Верни не больше N строк (сколько записей вернуть)
        offset M - Пропусти первые M строк, потом начинай возвращать результат (сколько записей пропустить)
        ”"""
        page = max(1, page)
        limit = self.PAGE_SIZE
        offset = (page - 1) * limit

        rentals = await self.rental_repo.list_recent_with_details_for_admins(limit=limit + 1, offset=offset)

        has_next = len(rentals) > limit
        rentals = rentals[:limit]

        rows: List[RentalAdminDetailsOut] = []
        for r in rentals:
            rows.append(RentalAdminDetailsOut(
                rental=RentalOut.model_validate(r),
                item=ItemOut.model_validate(r.item),
                owner=UserOut.model_validate(r.owner),
                renter=UserOut.model_validate(r.renter)
            ))

        return rows, has_next

    async def get_details(self, rental_id: int, *, strict: bool = False) -> Optional[RentalAdminDetailsOut]:
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

    async def admin_cancel_rental(self, rental_id: int, admin_id: int, reason: str, *, strict: bool = False) -> bool:
        """Эта функция — властное вмешательство платформы в жизненный цикл сделки,
        когда нормальные пользовательские сценарии уже не работают
        или не должны работать. Это рычаг платформы, а не кнопка пользователя. Может происходить в любой момент.

        1) Сделка застряла: арендатор пропал | владелец не отвечает | статус висит неделями
        2) Нарушение правил: фейковое объявление | запрещённый предмет | мошенничество
        3) Спор, который нельзя “разрулить автоматически”
        4) Юридическая/репутационная защита
        """

        r = await self.rental_repo.get_by_id(rental_id)
        if not r:
            if strict:
                raise NotFoundError(f"Сделка не найдена: id={rental_id}")
            return False

        terminal_block = self._TERMINAL_STATUSES_
        if r.status in terminal_block:
            if strict:
                raise ConflictError("Сделку нельзя отменить: она в терминальном статусе")
            return False

        status_map = self._CANCEL_STATUS_MAP_
        new_status = status_map.get(r.status)
        if new_status is None:
            if strict:
                raise ConflictError("Сделку нельзя отменить из текущего статуса")
            return False

        updated = await self.rental_repo.update(rental_id, RentalUpdate(status=new_status)) # RentalStatus.CANCELLED_BY_OWNER
        if not updated: # логируем действие администратора только если изменение реально применилось
            if strict:
                raise ConflictError("Не удалось отменить сделку (возможно, уже изменена)")
            return False

        await self.admin_service.log_action(
            admin_id=admin_id,
            action_type=AdminActionType.ADMIN_CANCEL_RENTAL,
            entity_type=AdminEntityType.RENTAL,
            entity_id=rental_id,
            note=f"Admin cancel rental #{rental_id}",
            payload={
                "reason": reason,
                "from_status": r.status.value,
                "to_status": new_status.value
            }
        )

        logger.info("Admin cancelled rental id=%s from=%s to=%s", rental_id, r.status.value, new_status.value)
        return True

    async def admin_resolve_dispute(
            self,
            rental_id: int,
            admin_id: int,
            resolution: str,
            target_status: RentalStatus,
            strict: bool = False
    ) -> bool:
        """В карточке сделки (если статус DISPUTED) появляется кнопка “✅ Закрыть спор”
        Админ нажимает → бот просит текст решения (FSM)
        После ввода текста → бот показывает кнопки выбора исхода:
            - “➡️ Перевести в ACTIVE”
            - “✅ Завершить (COMPLETED)”
            - “↩️ Вернуть в CONFIRMED” (если этот статус у тебя есть)

        Нажатие кнопки → выполняется изменение статуса только по whitelist-статусам,
        пишется audit log, перерисовывается карточка сделки."""

        r = await self.rental_repo.get_by_id(rental_id)
        if not r:
            if strict:
                raise NotFoundError(f"Сделка не найдена: id={rental_id}")
            return False

        # закрываем спор только если он открыт
        if r.status != RentalStatus.DISPUTED:
            if strict:
                raise ConflictError("Спор можно закрыть только если статус DISPUTED")
            return False

        allowed_targets = self._ALLOWED_TARGETS_
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
            admin_id=admin_id,
            action_type=AdminActionType.RESOLVE_DISPUTE,
            entity_type=AdminEntityType.RENTAL,
            entity_id=rental_id,
            note=f"Resolve dispute for rental #{rental_id}",
            payload={
                "resolution": resolution,
                "from_status": r.status.value,
                "to_status": target_status.value
            },
        )

        logger.info("Admin resolved dispute rental id=%s to=%s", rental_id, target_status.value)
        return True
