import logging
from typing import Optional
from datetime import datetime, timezone

from db.repositories.rental import RentalRepository

from schemas.rental import RentalCreate, RentalUpdate, RentalOut, RentalDetailsOut
from schemas.item import ItemOut
from schemas.user import UserOut
from status.rental_status import RentalStatus, is_open_status, can_transition, status_timestamp_fields
from utils.domain_exceptions import ItemNotAvailable
from utils.errors import NotFoundError, ForbiddenError, ConflictError, ValidationError

"""
    list_rentals_by_renter - Возвращает все аренды, где пользователь — арендатор
    list_rentals_by_owner - Возвращает список аренд, где пользователь — владелец

    list_user_rentals - Возвращает все сделки пользователя (как арендатор + как владелец) с указанием роли пользователя 
    в каждой сделке
    
"""

logger = logging.getLogger(__name__)

class RentalService:
    """Сервис для работы с заявками клиентов на аренду товаров компании."""

    def __init__(self, rental_repo: RentalRepository):
        self.repo = rental_repo

    # ────────────────────────────────────────── DTO helpers ──────────────────────────────────────────────────────────
    @staticmethod
    def _to_out(rental) -> RentalOut:
        return RentalOut.model_validate(rental)

    @classmethod
    def _to_out_list(cls, rentals) -> list[RentalOut]:
        return [cls._to_out(rental) for rental in rentals]

    @classmethod
    def _to_details(cls, rental) -> RentalDetailsOut:
        return RentalDetailsOut(
            rental=RentalOut.model_validate(rental),
            item=ItemOut.model_validate(rental.item),
            user=UserOut.model_validate(rental.user),
        )

    # ─────────────────────────────────────── Business validation ─────────────────────────────────────────────────────
    @staticmethod
    def _validate_transition(old_status: RentalStatus, new_status: RentalStatus, *, strict: bool) -> bool:
        if can_transition(old_status, new_status):
            return True
        if strict:
            raise ConflictError(f"Нельзя изменить статус заявки: {old_status.value} -> {new_status.value}")
        return False

    @staticmethod
    def _validate_date_create(data: RentalCreate) -> None:
        if data.start_date and data.end_date and data.end_date <= data.start_date:
            raise ValidationError("Дата окончания аренды должна быть позже даты начала")

    # ────────────────────────────────────────── Read methods ──────────────────────────────────────────────────────────
    async def get_by_id(self, rental_id: int, *, strict: bool = False) -> Optional[RentalOut]:
        """Вернуть заявку  по ID"""
        rental = await self.repo.get_by_id(rental_id)
        if not rental:
            if strict:
                raise NotFoundError(f"Заявка не найдена: id={rental_id}")
            return None

        return self._to_out(rental)

    async def list_rentals_by_user(self, user_id: int) -> list[RentalOut]:
        """Вернуть заявки клиента."""
        rentals = await self.repo.list_by_user_id(user_id)
        return self._to_out_list(rentals)

    async def get_rental_details(self, rental_id: int, current_user_id: int, *, strict: bool = False) -> Optional[RentalDetailsOut]:
        """Вернуть подробную информацию о заявке клиенту, который её создал."""
        rental = await self.repo.get_details_by_id(rental_id)
        if not rental:
            if strict:
                raise NotFoundError(f"Заявка не найдена: id={rental_id}")
            return None

        # Проверяем право доступа
        if rental.user_id != current_user_id:
            if strict:
                raise ForbiddenError("Нет доступа к сделке")
            return None

        return self._to_details(rental)

    # ─────────────────────────────────────────── write methods ────────────────────────────────────────────────────────
    async def create(self, data: RentalCreate) -> RentalOut:
        """Создать новую заявку клиента."""
        self._validate_date_create(data)
        rental = await self.repo.create(data)

        dto = self._to_out(rental)
        logger.info("Создана заявка: id=%s user_id=%s item_id=%s", dto.id, dto.user_id, dto.item_id)
        return dto

    # мб лучше не разрешать это клиенту?
    async def update(self, rental_id: int, data: RentalUpdate, *, strict: bool = False) -> Optional[RentalOut]:
        """Обновить заявку."""
        obj = await self.repo.update(rental_id, data)
        if not obj:
            if strict:
                raise NotFoundError(f"Заявка не найдена: id={rental_id}")
            return None

        dto = self._to_out(obj)
        logger.info("Заявка обновлена: id=%s", dto.id)
        return dto

    # delete() - запрещено

    # Переход REQUESTED / IN_PROGRESS / CONFIRMED → CANCELLED_BY_CLIENT (Клиент отменяет свою заявку до фактической выдачи товара)
    async def cancel_by_client(self, rental_id: int, user_id: int, *, strict: bool = False) -> bool:
        """Отменить заявку клиентом."""

        rental = await self.repo.get_by_id(rental_id)
        if not rental:
            if strict:
                raise NotFoundError(f"Заявка не найдена: id={rental_id}")
            return False

        if rental.user_id != user_id:
            if strict:
                raise ForbiddenError("Нет доступа к заявке")
            return False

        new_status = RentalStatus.CANCELLED_BY_CLIENT
        old_status = rental.status
        if old_status == new_status:
            return True

        if not self._validate_transition(old_status, new_status, strict=strict):
            return False

        updated = await self.repo.try_update_status_if_user(rental_id, user_id, new_status, expected_status=old_status)
        if not updated:
            if strict:
                raise ConflictError("Не удалось отменить заявку")
            return False

        await self.repo.update(rental_id, self._build_status_update(new_status))

        logger.info("Заявка отменена клиентом: id=%s user_id=%s", rental_id, user_id)
        return True

    # ───────────────────────────────────── Admin-Rental logic 🔧 ──────────────────────────────────────────────────────
    # Внутренний метод — ORM для доменной логики
    async def _get_open_rental_for_item(self, item_id: int):
        """Вернуть первую открытую заявку по товару или None.

        Внутренний метод: возвращает ORM-модель"""
        rentals = await self.repo.list_recent_open_by_item_id(item_id)

        for rental in rentals:
            if is_open_status(rental.status):
                return rental

        return None

    # Публичный метод — только DTO
    async def get_open_rental_for_item(self, item_id: int) -> Optional[RentalOut]:
        """Вернуть первую открытую заявку по товару в виде DTO или None."""
        rental = await self._get_open_rental_for_item(item_id)
        if rental is None:
            return None

        return self._to_out(rental)

    async def ensure_item_available(self, item_id: int) -> None:
        """Проверить, что по товару нет открытой заявки.

        Для текущего MVP считаем: один товар = одна активная доступная единица.
        """
        open_rental = await self._get_open_rental_for_item(item_id)
        if not open_rental:
            return

        raise ItemNotAvailable(
            item_id=item_id,
            rental_id=open_rental.id,
            status=open_rental.status,
            end_date=open_rental.end_date,
        )

    async def has_open_rentals_for_item(self, item_id: int) -> bool:
        """Проверить, есть ли у item открытые аренды"""
        return await self.repo.has_open_rentals_for_item(item_id)