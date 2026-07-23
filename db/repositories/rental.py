from typing import Optional, Sequence
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from db.models.rental import Rental
from db.repositories.base import BaseRepository

from schemas.rental import RentalCreate, RentalUpdate, RentalStatusUpdate
from status.rental_status import RentalStatus


class RentalRepository(BaseRepository):
    """Репозиторий заявок клиентов на аренду товаров компании."""

    # ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _apply_recent_order(stmt):
        """Стабильный порядок выдачи заявок: новые сначала."""
        return stmt.order_by(Rental.created_at.desc(), Rental.id.desc())

    @staticmethod
    def _apply_pagination(stmt, *, limit: Optional[int], offset: int):
        if limit is not None:
            stmt = stmt.limit(limit).offset(offset)
        return stmt

    @staticmethod
    def _apply_status_filter(stmt, status: RentalStatus):
        """Оставить только заявки с указанным статусом."""
        return stmt.where(Rental.status == status)

    @staticmethod
    def _apply_item_filter(stmt, item_id: int):
        """Оставить только заявки по товару."""
        return stmt.where(Rental.item_id == item_id)

    @staticmethod
    def _apply_user_filter(stmt, user_id: int):
        """Оставить только заявки клиента."""
        return stmt.where(Rental.user_id == user_id)

    @staticmethod
    def _apply_assigned_admin_filter(stmt, admin_id: int):
        """Оставить только заявки, назначенные менеджеру."""
        return stmt.where(Rental.assigned_admin_id == admin_id)

    @staticmethod
    def _with_details(stmt):
        """Подгрузить связи заявки, пока сессия живая."""
        return stmt.options(
            selectinload(Rental.item), # товар - #.selectinload(Item.price_tiers), # товар и тарифы,
            selectinload(Rental.user), # клиент
            selectinload(Rental.assigned_admin), # назначенный менеджер
        )

    # ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    async def list_all(self, *, limit: Optional[int] = None, offset: int = 0) -> list[Rental]:
        """Вернуть все заявки клиентов."""
        async with self._session() as s:
            stmt = select(Rental)
            stmt = self._apply_recent_order(stmt)
            stmt = self._apply_pagination(stmt, limit=limit, offset=offset)

            return await self._list(s, stmt)

    async def get_by_id(self, rental_id: int) -> Optional[Rental]:
        """Найти заявку по ID"""
        async with self._session() as s:
            return await s.get(Rental, rental_id)

    async def list_by_item_id(self, item_id: int, *, limit: Optional[int] = None, offset: int = 0) -> list[Rental]:
        """Вернуть заявки по товару."""
        async with self._session() as s:
            stmt = select(Rental)
            stmt = self._apply_item_filter(stmt, item_id)
            stmt = self._apply_recent_order(stmt)
            stmt = self._apply_pagination(stmt, limit=limit, offset=offset)

            return await self._list(s, stmt)

    async def list_by_user_id(self, user_id: int, *, limit: Optional[int] = None, offset: int = 0) -> list[Rental]:
        """Вернуть заявки клиента."""
        async with self._session() as s:
            stmt = select(Rental)
            stmt = self._apply_user_filter(stmt, user_id)
            stmt = self._apply_recent_order(stmt)
            stmt = self._apply_pagination(stmt, limit=limit, offset=offset)

            return await self._list(s, stmt)

    async def list_by_assigned_admin_id(self, admin_id: int, *, limit: Optional[int] = None, offset: int = 0) -> list[Rental]:
        """Вернуть заявки, назначенные менеджеру."""
        async with self._session() as s:
            stmt = select(Rental)
            stmt = self._apply_assigned_admin_filter(stmt, admin_id)
            stmt = self._apply_recent_order(stmt)
            stmt = self._apply_pagination(stmt, limit=limit, offset=offset)

            return await self._list(s, stmt)

    async def list_by_status(self, status: RentalStatus, *, limit: Optional[int] = None, offset: int = 0) -> list[Rental]:
        """Заявки по статусу"""
        async with self._session() as s:
            stmt = select(Rental)
            stmt = self._apply_status_filter(stmt, status)
            stmt = self._apply_recent_order(stmt)
            stmt = self._apply_pagination(stmt, limit=limit, offset=offset)

            return await self._list(s, stmt)

    async def get_details_by_id(self, rental_id: int) -> Optional[Rental]:
        """Вернуть заявку с заранее подгруженными товаром, клиентом и назначенным менеджером."""
        async with self._session() as s:
            stmt = select(Rental).where(Rental.id == rental_id)
            stmt = self._with_details(stmt)

            return await self._one_or_none(s, stmt)


    # ──────────────────────────────────────────── Для admin-панели ────────────────────────────────────────────────────
    async def list_recent(self, *, limit: int, offset: int = 0) -> list[Rental]:
        """Последние заявки клиентов."""
        async with self._session() as s:
            stmt = select(Rental)
            stmt = self._apply_recent_order(stmt)
            stmt = self._apply_pagination(stmt, limit=limit, offset=offset)

            return await self._list(s, stmt)

    async def list_recent_with_details_for_admins(self, *, limit: int, offset: int) -> list[Rental]:
        """Последние заявки для админ-панели с заранее подгруженными связями."""
        async with self._session() as s:
            stmt = select(Rental)
            stmt = self._apply_recent_order(stmt)
            stmt = self._apply_pagination(stmt, limit=limit, offset=offset)
            stmt = self._with_details(stmt)

            return await self._list(s, stmt)

    async def list_by_status_with_details_for_admins(self, status: RentalStatus, *, limit: int, offset: int) -> list[Rental]:
        """Заявки указанного статуса для админ-панели с заранее подгруженными связями."""
        async with self._session() as s:
            stmt = select(Rental)
            stmt = self._apply_status_filter(stmt, status)
            stmt = self._apply_recent_order(stmt)
            stmt = self._apply_pagination(stmt, limit=limit, offset=offset)
            stmt = self._with_details(stmt)

            return await self._list(s, stmt)

    # ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    async def create(self, rental_data: RentalCreate, *, status: RentalStatus = RentalStatus.REQUESTED) -> Rental:
        """Создать новую заявку клиента на аренду товара (с явно заданным начальным статусом!)."""
        payload = rental_data.model_dump()
        payload["status"] = status
        async with self._session() as s:
            obj = Rental(**payload)
            # obj = Rental(**rental_data.model_dump(exclude_none=True))
            return await self._add_commit_refresh(s, obj)

    async def update(self, rental_id: int, update_data: RentalUpdate) -> Optional[Rental]:
        """Обновить заявку.

        Возвращает Rental — если заявка найдена.
        Возвращает текущий объект без commit — если patch пустой или значения не изменились.
        Возвращает None — если заявка не найдена.
        """
        async with self._session() as s:
            obj: Optional[Rental] = await s.get(Rental, rental_id)
            if not obj:
                return None

            data = update_data.model_dump(exclude_unset=True)
            if not data:
                return obj

            changed = False
            for field_name, value in data.items():
                if getattr(obj, field_name) != value:
                    setattr(obj, field_name, value)
                    changed = True

            if not changed:
                return obj

            return await self._commit_refresh(s, obj)

    async def delete(self, rental_id: int) -> bool:
        """Удалить заявку по id.

        Возвращает True — удалена.
        Возвращает False — не найдена.
        """
        async with self._session() as s:
            obj = await s.get(Rental, rental_id)
            if not obj:
                return False

            return await self._delete_commit(s, obj)

    # ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # полностью перенесена в сервис: _build_status_update() - Собрать схему обновления статуса

    # старые названия: try_update_status / try_update_status_if_user
    async def apply_update_if_current_status(
            self,
            rental_id: int,
            expected_status: RentalStatus,
            update_data: RentalStatusUpdate,
    ) -> bool:
        """Атомарно применить подготовленный patch, если текущий статус не изменился."""
        """Атомарно обновить статус заявки, если текущий статус совпадает с ожидаемым."""
        data = update_data.model_dump(exclude_unset=True)
        if not data:
            return False

        async with self._session() as s:
            stmt = (
                update(Rental)
                .where(Rental.id == rental_id)
                .where(Rental.status == expected_status)
                .values(**data)
            )
            return await self._execute_update_commit(s, stmt)

    async def apply_update_if_user_and_current_status(
            self,
            rental_id: int,
            user_id: int,
            expected_status: RentalStatus,
            update_data: RentalStatusUpdate,
    ) -> bool:
        """Атомарно применить подготовленный patch заявки клиента, если статус не изменился."""
        """Атомарно обновить статус заявки, если она принадлежит клиенту и статус совпадает с ожидаемым."""
        data = update_data.model_dump(exclude_unset=True)
        if not data:
            return False

        async with self._session() as s:
            stmt = (
                update(Rental)
                .where(Rental.id == rental_id)
                .where(Rental.user_id == user_id)
                .where(Rental.status == expected_status)
                .values(**data)
            )
            return await self._execute_update_commit(s, stmt)

    """
    1. создаёт RentalStatusUpdate через _build_status_update()
    2. схема понимает: для CANCELLED_BY_CLIENT нужны cancelled_at и closed_at
    3. превращает RentalStatusUpdate в patch через model_dump(exclude_unset=True)
    4. делает один SQL UPDATE
    """

    """
    Возможно на будущее: параметры для уведомлений (на будущее)
     - notify_recipient_role: Optional[str] = None,  # 'renter', 'owner', 'other'
     - notify_message_template: Optional[str] = None,
     - notify_button_text: Optional[str] = None,
     - notify_button_callback_action: Optional[str] = None
    """

    # ─────────────────────────────────────────── Удаляем? ─────────────────────────────────────────────────────────────
    # async def release_item_quantity(self, *, item_id: int, quantity: int) -> bool:
    #     """Вернуть зарезервированное количество товара в доступный остаток."""
    #     if quantity < 1:
    #         return False
    #     async with self._session() as s:
    #         stmt = (
    #             update(Item)
    #             .where(Item.id == item_id)
    #             .values(available_quantity=Item.available_quantity + quantity)
    #         )
    #         return await self._execute_update_commit(s, stmt)



    # ─────────────────────────────── Пока не используемые ─────────────────────────────────────────────────────────────
    @staticmethod
    def _apply_statuses_filter(stmt, statuses: Sequence[RentalStatus]):
        """Оставить только заявки с одним из указанных статусов."""
        return stmt.where(Rental.status.in_(tuple(statuses)))

    # async def list_by_user_id(
    #         self,
    #         user_id: int,
    #         statuses: Optional[Sequence[RentalStatus]] = None,
    #         *,
    #         limit: Optional[int] = 20,
    #         offset: int = 0,
    # ) -> list[Rental]:
    #     """Вернуть заявки клиента, при необходимости ограничив список статусами."""
    #     async with self._session() as s:
    #         stmt = select(Rental)
    #         stmt = self._apply_user_filter(stmt, user_id)
    #         if statuses:
    #             stmt = self._apply_statuses_filter(stmt, statuses)
    #         stmt = self._apply_recent_order(stmt)
    #         stmt = self._apply_pagination(stmt, limit=limit, offset=offset)
    #
    #         return await self._list(s, stmt)

    async def list_by_statuses(self, statuses: Sequence[RentalStatus], *, limit: Optional[int] = 20, offset: int = 0) -> list[Rental]:
        """Вернуть заявки с одним из указанных статусов."""
        if not statuses:
            return []

        async with self._session() as s:
            stmt = select(Rental)
            stmt = self._apply_statuses_filter(stmt, statuses)
            stmt = self._apply_recent_order(stmt)
            stmt = self._apply_pagination(stmt, limit=limit, offset=offset)

            return await self._list(s, stmt)

    # async def get_by_id_with_details(self, rental_id: int) -> Optional[Rental]:
    #     """Вернуть заявку с заранее подгруженными товаром, клиентом и назначенным менеджером."""
    #     async with self._session() as s:
    #         stmt = select(Rental).where(Rental.id == rental_id)
    #         stmt = self._with_details(stmt)
    #
    #         return await self._one_or_none(s, stmt)
    #
    # async def get_details_by_id(self, rental_id: int) -> Optional[Rental]:
    #     """Alias для обратной совместимости: заявка с заранее подгруженными связями."""
    #     return await self.get_by_id_with_details(rental_id)
