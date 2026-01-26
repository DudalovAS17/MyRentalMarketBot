import logging
from datetime import datetime, timezone
from typing import Optional, List, Any

from db.models.rental import RentalStatus
from db.repositories.rental import RentalRepository
from services.item_service import ItemService
from services.user_service import UserService
from services.admin_service import AdminActionService
from schemas.rental import RentalUpdate

logger = logging.getLogger(__name__)

class AdminRentalService:
    """
    Админский сервис по сделкам:
    - листинг последних
    - просмотр по id
    - cancel / resolve_dispute
    """

    PAGE_SIZE = 8

    def __init__(
        self,
        rental_repo: RentalRepository,
        item_service: ItemService,
        user_service: UserService,
        admin_service: AdminActionService,
    ):
        self.rental_repo = rental_repo
        self.item_service = item_service
        self.user_service = user_service
        self.admin_service = admin_service

    async def list_recent_rentals(self, page: int) -> tuple[list[dict[str, Any]], bool]: # List[dict]:
        """“админ-экран: последние сделки

        - переводит page в SQL-параметры limit и offset
        - берёт сделки из БД в порядке “самые новые сверху”
        - определяет есть ли следующая страница
        - подготавливает список строк (rows), который потом handler рисует

        limit N - Верни не больше N строк (сколько записей вернуть)
        offset M - Пропусти первые M строк, потом начинай возвращать результат (сколько записей пропустить)
        ”"""

        page = max(1, page) # это как бы страховка, чтобы не было корявых значений
        limit = self.PAGE_SIZE
        offset = (page - 1) * limit # Если PAGE_SIZE = 10, page = 1 → offset = 0 (страница 1 показывает первые 10 строк результата)

        rentals = await self.rental_repo.list_recent(limit=limit + 1, offset=offset)
        # тебе нужно показать 10 сделок на странице, ты запрашиваешь 11
        #   - Если пришло 11 строк → значит есть следующая страница
        #   - Если пришло 10 или меньше → следующей страницы нет

        has_next = len(rentals) > limit
        rentals = rentals[:limit] # Он нужен только для has_next, но не должен попадать в UI (отбрасывает 11-й элемент)

        rows: List[dict] = []
        for r in rentals:
            item = await self.item_service.get_item_by_id(r.item_id)
            owner = await self.user_service.get_by_id(r.owner_id)
            renter = await self.user_service.get_by_id(r.renter_id)

            rows.append(
                {
                    "rental": r,
                    "item": item,
                    "owner": owner,
                    "renter": renter,
                }
            ) # тут нагрузка !!! - много (N+1) запросов одновременно, т.к.4 объекта. Надо будет решать

        return rows, has_next # список строк, булево

    async def get_details(self, rental_id: int) -> Optional[dict]:
        r = await self.rental_repo.get_by_id(rental_id)
        if not r:
            return None
        item = await self.item_service.get_item_by_id(r.item_id)
        owner = await self.user_service.get_by_id(r.owner_id)
        renter = await self.user_service.get_by_id(r.renter_id)
        return {"rental": r, "item": item, "owner": owner, "renter": renter}

    async def admin_cancel_rental(self, rental_id: int, admin_id: int, reason: str) -> bool:
        """Эта функция — властное вмешательство платформы в жизненный цикл сделки,
        когда нормальные пользовательские сценарии уже не работают
        или не должны работать. Это рычаг платформы, а не кнопка пользователя. Может происходить в любой момент.

        1) Сделка застряла: арендатор пропал | владелец не отвечает | статус висит неделями
        2) Нарушение правил: фейковое объявление | запрещённый предмет | мошенничество
        3) Спор, который нельзя “разрулить автоматически”
        4) Юридическая/репутационная защита
        """

        r = await self.rental_repo.get_by_id(rental_id)
        if not r: # нечего отменять
            return False

        if r.status == RentalStatus.COMPLETED: # не отменяем завершённые
            return False

        # Имеем ли мы право вмешиваться сейчас. Это множество состояний, в которых сделка уже завершена по смыслу.
        terminal_block = {
            RentalStatus.COMPLETED,
            RentalStatus.REJECTED_BY_OWNER,
            RentalStatus.REJECTED_BY_RENTER,
            RentalStatus.CANCELLED_BY_OWNER,
            RentalStatus.CANCELLED_BY_RENTER,
            RentalStatus.CANCELLED_CONFIRMED_BY_OWNER,
            RentalStatus.CANCELLED_CONFIRMED_BY_RENTER,
        }
        if r.status in terminal_block:
            return False

        # Что именно означает “отмена” на этом этапе
        # (пока так: не добавляли статусы "Админ отменил", а используем эти, но в audit будет видно, что админ отменил)
        status_map = {
            RentalStatus.REQUESTED: RentalStatus.REJECTED_BY_OWNER, # REQUESTED → REJECTED_BY_OWNER
            RentalStatus.CONFIRMED: RentalStatus.CANCELLED_CONFIRMED_BY_OWNER,
            RentalStatus.ACTIVE: RentalStatus.CANCELLED_BY_OWNER,
            RentalStatus.DISPUTED: RentalStatus.CANCELLED_BY_OWNER,
        }
        new_status = status_map.get(r.status)

        if new_status is None:
            return False

        updated = await self.rental_repo.update(rental_id, RentalUpdate(status=RentalStatus.CANCELLED_BY_OWNER))
        if not updated: # логируем действие администратора только если изменение реально применилось.
            return False

        await self.admin_service.log_action(
            admin_id=admin_id,
            action_type="ADMIN_CANCEL_RENTAL",
            entity_type="rental",
            entity_id=rental_id,
            payload={
                "reason": reason,
                "from_status": r.status.value,
                "to_status": new_status.value
            }
        )
        return True

    async def admin_resolve_dispute(
            self,
            rental_id: int,
            admin_id: int,
            resolution: str,
            target_status: RentalStatus
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
            return False

        # закрываем спор только если он открыт
        if r.status != RentalStatus.DISPUTED:
            return False

        # допустимые исходы для "закрытия спора"
        allowed_targets = {RentalStatus.ACTIVE, RentalStatus.COMPLETED, RentalStatus.CONFIRMED}
        if target_status not in allowed_targets:
            return False

        updated = await self.rental_repo.update(rental_id, RentalUpdate(status=target_status))
        if not updated:
            return False

        await self.admin_service.log_action(
            admin_id=admin_id,
            action_type="RESOLVE_DISPUTE",
            entity_type="rental",
            entity_id=rental_id,
            payload={
                "resolution": resolution,
                "from_status": r.status.value, # getattr(r.status, "value", str(r.status)),
                "to_status": target_status.value # getattr(target_status, "value", str(target_status)),
            },
        )
        return True
