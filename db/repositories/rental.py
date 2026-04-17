from typing import Optional
from sqlalchemy import select, update, or_, exists, and_
from sqlalchemy.orm import selectinload

from db.models.rental import Rental
from db.repositories.base import BaseRepository

from schemas.rental import RentalCreate, RentalUpdate
from status.rental_status import RentalStatus, RentalActorRole, is_open_status


class RentalRepository(BaseRepository):
    """Репозиторий для работы с арендами (сделками)"""

    _OPEN_RENTAL_LOOKUP_LIMIT = 10
    # ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    async def list_all(self) -> list[Rental]:
        """Вернуть все сделки"""
        async with self._session() as s:
            return await self._list(s, select(Rental))

    async def get_by_id(self, rental_id: int) -> Optional[Rental]:
        """Найти сделку по ID"""
        async with self._session() as s:
            return await s.get(Rental, rental_id)

    async def list_by_item_id(self, item_id: int) -> list[Rental]:
        """Все сделки по конкретной вещи = Получение аренд по ID вещи"""
        async with self._session() as s:
            stmt = select(Rental).where(Rental.item_id == item_id)
            return await self._list(s, stmt)

    async def list_by_renter_id(self, renter_id: int) -> list[Rental]:
        """Сделки, где пользователь — арендатор"""
        async with self._session() as s:
            stmt = select(Rental).where(Rental.renter_id == renter_id)
            return await self._list(s, stmt)

    async def list_by_owner_id(self, owner_id: int) -> list[Rental]:
        """Сделки, где пользователь — владелец"""
        async with self._session() as s:
            stmt = select(Rental).where(Rental.owner_id == owner_id)
            return await self._list(s, stmt)

    async def list_by_user_id(self, user_id: int) -> list[Rental]:
        """Все сделки, где пользователь — арендатор или владелец"""
        async with self._session() as s:
            stmt = (
                select(Rental)
                .where(or_(Rental.renter_id == user_id, Rental.owner_id == user_id))
                .order_by(Rental.created_at.desc())
            )
            return await self._list(s, stmt)

    async def list_by_status(self, status: RentalStatus) -> list[Rental]:
        """Сделки по статусу"""
        async with self._session() as s:
            stmt = select(Rental).where(Rental.status == status)
            return await self._list(s, stmt)

    async def get_details_by_id(self, rental_id: int) -> Optional[Rental]:
        """Позволяет убрать зависимость сервиса сделок от сервисов объявлений, пользователей и тд.

        “Подгрузи эти связи заранее, пока сессия живая”
        """
        async with self._session() as s:
            stmt = (
                select(Rental)
                .where(Rental.id == rental_id)
                .options(
                    selectinload(Rental.item),
                    selectinload(Rental.renter),
                    selectinload(Rental.owner),
                )
            )
            return await self._one_or_none(s, stmt)

    # ──────────────────────────────────────────── Для admin-панели ────────────────────────────────────────────────────
    async def list_recent(self, *, limit: int, offset: int = 0) -> list[Rental]:
        """Последние сделки (по убыванию created_at)"""
        async with self._session() as s:
            stmt = (
                select(Rental)
                #.order_by(Rental.created_at.desc())
                .order_by(Rental.created_at.desc(), Rental.id.desc())
                .limit(limit)
                .offset(offset)
            )
            return await self._list(s, stmt)

    async def list_recent_with_details_for_admins(self, *, limit: int, offset: int) -> list[Rental]:
        """Последние сделки для админ-панели с заранее подгруженными связями - для сервиса admin_rental_service"""
        async with self._session() as s:
            stmt = (
                select(Rental)
                .order_by(Rental.created_at.desc()) # , Rental.id.desc()
                .limit(limit)
                .offset(offset)
                .options(
                    selectinload(Rental.item),
                    selectinload(Rental.owner),
                    selectinload(Rental.renter),
                )
            )
            return await self._list(s, stmt)

    # ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    async def create(self, rental_data: RentalCreate) -> Rental:
        """Создать новую сделку"""
        async with self._session() as s:
            obj = Rental(**rental_data.model_dump())
            return await self._add_commit_refresh(s, obj)

    async def update(self, rental_id: int, update_data: RentalUpdate) -> Optional[Rental]:
        """Обновить сделку.

        Возвращает Rental — если изменения применены.
        Возвращает текущий объект без изменений - если `update_data` пустой
        Возвращает None — если сделка не найдена или изменений нет.
        """
        async with self._session() as s:
            obj: Optional[Rental] = await s.get(Rental, rental_id)
            if not obj:
                return None

            data = update_data.model_dump(exclude_unset=True)
            if not data:
                return obj

            for k, v in data.items():
                setattr(obj, k, v)

            return await self._commit_refresh(s, obj)

    async def delete(self, rental_id: int) -> bool:
        """Удалить сделку по id.

        Возвращает True — удалена.
        Возвращает False — не найдена.
        """
        async with self._session() as s:
            obj = await s.get(Rental, rental_id)
            if not obj:
                return False

            return await self._delete_commit(s, obj)

    # ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    async def try_update_status(self, *,
        rental_id: int, # какую сделку мы хотим изменить
        new_status: RentalStatus, # переводим в этот статус
        expected_status: RentalStatus, # из какого статуса разрешён переход
        actor_user_id: int, # кто нажал кнопку (текущий пользователь)
        actor_role: RentalActorRole,  # чьё это право (owner/renter)

        # Параметры для уведомлений (на будущее)
        #notify_recipient_role: Optional[str] = None,  # 'renter', 'owner', 'other'
        #notify_message_template: Optional[str] = None,
        #notify_button_text: Optional[str] = None,
        #notify_button_callback_action: Optional[str] = None
    ) -> bool:
        """Атомарно обновить статус сделки, если совпали ожидаемый текущий статус и участник, уже проверенные сервисом."""

        match actor_role:
            case RentalActorRole.OWNER:
                actor_col = Rental.owner_id
            case RentalActorRole.RENTER:
                actor_col = Rental.renter_id

        async with self._session() as s:
            stmt = (
                update(Rental)
                .where(Rental.id == rental_id)
                .where(actor_col == actor_user_id)
                .where(Rental.status == expected_status)
                .values(status=new_status)
            )
            return await self._execute_update_commit(s, stmt)

    async def try_update_status_if_participant(self, *,
        rental_id: int,
        new_status: RentalStatus,
        expected_status: RentalStatus,
        actor_user_id: int,
    ) -> bool:
        """Атомарно обновить статус сделки, если текущий пользователь является участником сделки и текущий статус совпадает с ожидаемым.

        Для DISPUTE (оба участника могут, в try_update_status только 1)
        """
        async with self._session() as s:
            stmt = (
                update(Rental)
                .where(Rental.id == rental_id)
                .where(or_(Rental.owner_id == actor_user_id, Rental.renter_id == actor_user_id))
                .where(Rental.status == expected_status)
                .values(status=new_status)
            )
            return await self._execute_update_commit(s, stmt)

    # ───────────────────────────────── Тут мы обновляем булевый флаг (не статус) ──────────────────────────────────────
    async def try_set_owner_handover_confirmed(self, *, rental_id: int, owner_id: int) -> bool:
        """Владелец отмечает: 'передал вещь' (только если CONFIRMED, и он owner, и флаг ещё False)

        Возвращает True - владелец подтвердил передачу
        """
        async with self._session() as s:
            stmt = (
                update(Rental)
                .where(Rental.id == rental_id)
                .where(Rental.owner_id == owner_id)
                .where(Rental.status == RentalStatus.CONFIRMED)
                .where(Rental.owner_handover_confirmed.is_(False))
                .values(owner_handover_confirmed=True)
            )
            return await self._execute_update_commit(s, stmt)

    async def try_set_renter_confirm_receive(self, *, rental_id: int, renter_id: int) -> bool:
        """Арендатор отмечает: 'получил вещь' (только если CONFIRMED, и он renter, и флаг ещё False)

        Возвращает True - арендатор подтвердил получение вещи
        """
        async with self._session() as s:
            stmt = (
                update(Rental)
                .where(Rental.id == rental_id)
                .where(Rental.renter_id == renter_id)
                .where(Rental.status == RentalStatus.CONFIRMED)
                .where(Rental.renter_receive_confirmed.is_(False))
                .values(renter_receive_confirmed=True)
            )
            return await self._execute_update_commit(s, stmt)

    async def try_activate_confirmed_rental(self, *, rental_id: int) -> bool:
        """CONFIRMED -> ACTIVE если обе стороны подтвердили передачу/получение

        Возвращает True - арендатор подтвердил получение (статус перешёл в ACTIVE)
        """
        async with self._session() as s:
            stmt = (
                update(Rental)
                .where(Rental.id == rental_id)
                .where(Rental.status == RentalStatus.CONFIRMED)
                .where(Rental.owner_handover_confirmed.is_(True))
                .where(Rental.renter_receive_confirmed.is_(True))
                .values(status=RentalStatus.ACTIVE)
            )
            return await self._execute_update_commit(s, stmt)

    async def list_recent_open_by_item_id(self, item_id: int) -> list[Rental]:
        """Возвращает последние сделки по id"""
        async with self._session() as s:
            stmt = (
                select(Rental)
                .where(Rental.item_id == item_id)
                #.order_by(desc(Rental.id))
                .order_by(Rental.created_at.desc()) # , Rental.id.desc()
                .limit(self._OPEN_RENTAL_LOOKUP_LIMIT)
            )
            return await self._list(s, stmt)

    # ─────────────────────────────── For item-service: moderate_set_status() ──────────────────────────────────────────
    async def has_open_rentals_for_item(self, item_id: int) -> bool:
        """Техническая проверка: есть ли у item открытые сделки"""
        open_statuses = [st for st in RentalStatus if is_open_status(st)]

        async with self._session() as s:
            stmt = select(
                exists().where(
                    and_(
                        Rental.item_id == item_id,
                        Rental.status.in_(open_statuses),
                    )
                )
            )
            return bool(await s.scalar(stmt)) # return await self._exists(s, stmt) - лучше