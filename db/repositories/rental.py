from typing import Optional
from sqlalchemy import select, update, exists, and_
from sqlalchemy.orm import selectinload

from db.models.rental import Rental
from db.repositories.base import BaseRepository

from schemas.rental import RentalCreate, RentalUpdate
from status.rental_status import RentalStatus, open_statuses

"""try_set_owner_handover_confirmed
Владелец отмечает: 'передал вещь' (только если CONFIRMED, и он owner, и флаг ещё False)
Возвращает True - владелец подтвердил передачу

try_set_renter_confirm_receive
Арендатор отмечает: 'получил вещь' (только если CONFIRMED, и он renter, и флаг ещё False)
Возвращает True - арендатор подтвердил получение вещи

try_activate_confirmed_rental
CONFIRMED -> ACTIVE если обе стороны подтвердили передачу/получение
Возвращает True - арендатор подтвердил получение (статус перешёл в ACTIVE)
"""

class RentalRepository(BaseRepository):
    """Репозиторий заявок клиентов на аренду товаров компании."""

    _OPEN_RENTAL_LOOKUP_LIMIT = 10
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
    def _apply_open_status_filter(stmt):
        """Оставить только открытые заявки."""
        return stmt.where(Rental.status.in_(open_statuses()))

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
            selectinload(Rental.item), # товар
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
        """Найти сделку по ID"""
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
        """Сделки по статусу"""
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

    async def list_recent_open_by_item_id(self, item_id: int) -> list[Rental]:
        """Вернуть последние открытые заявки по товару."""
        async with self._session() as s:
            stmt = select(Rental)
            stmt = self._apply_item_filter(stmt, item_id)
            stmt = self._apply_open_status_filter(stmt)
            stmt = self._apply_recent_order(stmt)
            stmt = stmt.limit(self._OPEN_RENTAL_LOOKUP_LIMIT)
            return await self._list(s, stmt)

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

    # ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    async def create(self, rental_data: RentalCreate) -> Rental:
        """Создать новую заявку клиента на аренду товара."""
        async with self._session() as s:
            obj = Rental(**rental_data.model_dump())
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
    async def try_update_status(
            self,
            rental_id: int, # какую сделку мы хотим изменить
            new_status: RentalStatus, # переводим в этот статус
            expected_status: RentalStatus, # из какого статуса разрешён переход
            #*,
            # Параметры для уведомлений (на будущее)
            #notify_recipient_role: Optional[str] = None,  # 'renter', 'owner', 'other'
            #notify_message_template: Optional[str] = None,
            #notify_button_text: Optional[str] = None,
            #notify_button_callback_action: Optional[str] = None
    ) -> bool:
        """Атомарно обновить статус заявки, если текущий статус совпадает с ожидаемым."""
        async with self._session() as s:
            stmt = (
                update(Rental)
                .where(Rental.id == rental_id)
                .where(Rental.status == expected_status)
                .values(status=new_status)
            )
            return await self._execute_update_commit(s, stmt)

    async def try_update_status_if_user(
            self,
            rental_id: int,
            user_id: int,
            new_status: RentalStatus,
            expected_status: RentalStatus,
            #*,
    ) -> bool:
        """Атомарно обновить статус заявки, если она принадлежит клиенту и статус совпадает с ожидаемым."""
        async with self._session() as s:
            stmt = (
                update(Rental)
                .where(Rental.id == rental_id)
                .where(Rental.user_id == user_id)
                .where(Rental.status == expected_status)
                .values(status=new_status)
            )
            return await self._execute_update_commit(s, stmt)

    # ─────────────────────────────── For item-service: moderate_set_status() ──────────────────────────────────────────
    async def has_open_rentals_for_item(self, item_id: int) -> bool:
        """Проверить, есть ли у товара открытые заявки."""

        async with self._session() as s:
            stmt = select(
                exists().where(
                    and_(Rental.item_id == item_id, Rental.status.in_(open_statuses()))
                )
            )

            return await self._exists(s, stmt)