import logging
from typing import Callable, Optional, List #, Dict, Any
#from datetime import datetime
#from decimal import Decimal
from sqlalchemy import desc

from sqlalchemy import update, select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.rental import Rental, RentalStatus
from schemas.rental import RentalCreate, RentalUpdate #, RentalOut

logger = logging.getLogger(__name__)


class RentalRepository:
    """Репозиторий для работы с арендами (сделками)"""

    def __init__(self, session_factory: Callable[[], AsyncSession]) -> None:
        self._sf = session_factory

    async def get_all(self) -> List[Rental]:
        """Вернуть все сделки"""
        async with self._sf() as s:
            res = await s.execute(select(Rental))
            return list(res.scalars().all()) # .all()

    async def get_by_id(self, rental_id: int) -> Optional[Rental]:
        """Найти сделку по ID"""
        async with self._sf() as s:
            return await s.get(Rental, rental_id)

    async def get_by_item_id(self, item_id: int) -> List[Rental]:
        """Все сделки по конкретной вещи = Получение аренд по ID вещи"""
        async with self._sf() as s:
            stmt = select(Rental).where(Rental.item_id == item_id)
            res = await s.execute(stmt)
            return list(res.scalars().all())

    async def get_by_renter_id(self, renter_id: int) -> List[Rental]:
        """Сделки, где пользователь — арендатор"""
        async with self._sf() as s:
            stmt = select(Rental).where(Rental.renter_id == renter_id)
            res = await s.execute(stmt)
            return list(res.scalars().all())

    async def get_by_owner_id(self, owner_id: int) -> List[Rental]:
        """Сделки, где пользователь — владелец"""
        async with self._sf() as s:
            stmt = select(Rental).where(Rental.owner_id == owner_id)
            res = await s.execute(stmt)
            return list(res.scalars()) # .all() нужен?

    async def get_by_user_id(self, user_id: int) -> List[Rental]:
        """Все сделки, где пользователь — арендатор или владелец"""
        async with self._sf() as s:
            stmt = (
                select(Rental).where(
                or_(Rental.renter_id == user_id, Rental.owner_id == user_id)
            )
            .order_by(Rental.created_at.desc()) # добавил
            )
            res = await s.execute(stmt)
            return list(res.scalars().all())

    # для admin-панели
    async def list_recent(self, *, limit: int, offset: int = 0) -> List[Rental]:
        """Последние сделки по ..."""
        async with self._sf() as s:
            stmt = (
                select(Rental)
                .order_by(Rental.created_at.desc()) # по дате создания
                #.order_by(desc(Rental.id)) # по убыванию id
                # .order_by(Rental.created_at.desc(), Rental.id.desc()) # Более надёжный вариант
                .limit(limit)
                .offset(offset)
            )
            res = await s.execute(stmt)
            return list(res.scalars().all())

    async def get_by_status(self, status: RentalStatus) -> List[Rental]:
        """Сделки по статусу"""
        async with self._sf() as s:
            stmt = select(Rental).where(Rental.status == status)
            res = await s.execute(stmt)
            return list(res.scalars().all())

    async def create(self, rental_data: RentalCreate) -> Rental:
        """Создать новую сделку"""
        async with self._sf() as s:
            obj = Rental(**rental_data.model_dump())
            s.add(obj)

            try:
                await s.commit()
                await s.refresh(obj)
                logger.info("create() — сделка успешно создана, id=%s", obj.id)
                return obj
            except Exception as e:
                await s.rollback()
                logger.error("create() — ошибка при создании сделки: %s", e, exc_info=True)
                raise

    async def update(self, rental_id: int, update_data: RentalUpdate) -> int:
        """Обновить сделку. Возвращает 1 — если обновили, 0 — если не найдено или изменений нет"""
        async with self._sf() as s:
            obj = await s.get(Rental, rental_id)
            if not obj:
                logger.warning("update() — сделка id=%s не найдена", rental_id)
                return 0

            data = update_data.model_dump(exclude_unset=True)
            if not data:
                logger.info("update() — изменений для сделки id=%s нет", rental_id)
                return 0

            for k, v in data.items():
                setattr(obj, k, v)

            try:
                await s.commit()
                await s.refresh(obj)
                logger.info("update() — сделка id=%s успешно обновлена", rental_id)
                return 1
            except Exception as e:
                await s.rollback()
                logger.error("update() — ошибка при обновлении сделки id=%s: %s", rental_id, e, exc_info=True)
                raise

    async def delete(self, rental_id: int) -> int:
        """Удалить сделку по id. Возвращает 1 — удалена, 0 — не найдена"""
        async with self._sf() as s:
            obj = await s.get(Rental, rental_id)
            if not obj:
                logger.warning("delete() — сделка id=%s не найдена", rental_id)
                return 0

            try:
                await s.delete(obj)
                await s.commit()
                logger.info("delete() — сделка id=%s успешно удалена", rental_id)
                return 1
            except Exception as e:
                await s.rollback()
                logger.error("delete() — ошибка при удалении сделки id=%s: %s", rental_id, e, exc_info=True)
                raise

    async def update_status_if_allowed(self, *,
        rental_id: int, # какую сделку мы хотим изменить
        new_status: RentalStatus, # во что хотим перевести (например CONFIRMED)
        expected_status: RentalStatus, # из какого статуса разрешён переход
        actor_user_id: int, # кто нажал кнопку (текущий пользователь)
        actor_field: str,  # чьё это право ("owner_id" или "renter_id")
           # Параметры для уведомлений (на будущее)
           #notify_recipient_role: Optional[str] = None,  # 'renter', 'owner', 'other'
           #notify_message_template: Optional[str] = None,
           #notify_button_text: Optional[str] = None,
           #notify_button_callback_action: Optional[str] = None
    ) -> bool:
        """ обновляем статус сделки только если одновременно выполняются все условия:
        - rental существует
        - инициатор имеет права (owner/renter)
        - текущий статус тот, который ожидаем (например, REQUESTED)
        Если хотя бы одно условие не выполняется → ничего не меняется."""

        FIELD_MAP = {
            "owner_id": Rental.owner_id,
            "renter_id": Rental.renter_id,
        }
        actor_col = FIELD_MAP[actor_field]

        async with self._sf() as s:
            stmt = (
                update(Rental)
                .where(Rental.id == rental_id) # обновляем конкретную сделку
                #.where(getattr(Rental, actor_field) == actor_user_id) # Права проверяются на уровне БД, а не в Python
                .where(actor_col == actor_user_id) #
                .where(Rental.status == expected_status) # Это защита от: двойных кликов, устаревших кнопок, гонок (нет гонки между чтением и записью)
                .values(status=new_status) # Если и только если все WHERE совпали → статус обновляется
            )
            res = await s.execute(stmt)
            await s.commit()
            return (res.rowcount or 0) > 0
    """
    - нет гонок: две кнопки нажали — обновится только один раз
    - права на уровне БД (через WHERE owner_id/renter_id)
    - сервису не нужно вручную “проверять и потом обновлять” двумя запросами
    
    !!!!!!!!!!о строчке .where(getattr(Rental, actor_field) == actor_user_id) :
    a) getattr(Rental, actor_field) превращается в: Rental.owner_id или Rental.renter_id
    b) получим либо WHERE owner_id = :actor_user_id, либо WHERE renter_id = :actor_user_id
    Следствие:
        пользователь физически не может изменить чужую сделку
        даже если хендлер ошибся
        даже если кто-то подменит callback_data
        
    !!!!!!!!!!!о строчке .where(Rental.status == expected_status) :
    Пример:
        два человека нажали “Подтвердить”
        первый успел → статус стал CONFIRMED
        второй → WHERE status = REQUESTED уже не выполняется
        rowcount = 0
        ❗ Никаких “случайных” повторных подтверждений.
        
    !!!!!!!!!о строчке (res.rowcount or 0) > 0
    res.rowcount — сколько строк реально изменено
    True → статус действительно изменён
    False → не та роль
            не тот статус
            сделки нет
            кнопка устарела
    Сервис решает, что с этим делать (кинуть ошибку, показать alert).
    """
    # тут дальнейшее расширение связанное с уведомлениями
    """
    @staticmethod
    def _change_rental_status(
        rental_id: int,
        user_id: int,
        allowed_roles: List[str],
        allowed_current_statuses: List[RentalStatus],
        new_status: RentalStatus,
        action_name: str,
        # Параметры для уведомлений
        notify_recipient_role: Optional[str] = None,  # 'renter', 'owner', 'other'
        notify_message_template: Optional[str] = None,
        notify_button_text: Optional[str] = None,
        notify_button_callback_action: Optional[str] = None
    ) -> bool:
    ""Внутренний вспомогательный метод для изменения статуса аренды и отправки уведомления.""

    logger.warning(f"{action_name}: Аренда {rental_id} не найдена.")
    logger.warning(f"{action_name}: Пользователь {user_id} (роль: {current_user_role}) не "
                   f"имеет прав для действия с арендой {rental_id}. Требуется роль: {allowed_roles}")
    logger.warning(f"{action_name}: Недопустимый текущий статус {rental.status.value} "
                   f"для аренды {rental_id}. Допустимые: {[s.value for s in allowed_current_statuses]}")
    logger.info(f"{action_name}: Статус аренды {rental_id} успешно изменен с {original_status.value} "
                f"на {new_status.value} пользователем {user_id}")
    logger.error(f"Ошибка при выполнении {action_name} для аренды {rental_id}: {e}", exc_info=True)

    try:
        rental =

        # Определяем роль текущего пользователя
        current_user_role = "renter"/"owner"

        # Проверка прав
        if current_user_role not in allowed_roles:

        # Проверка текущего статуса
        if rental.status not in allowed_current_statuses:

        # Обновляем статус
        rental.status = new_status

    # Отправка уведомления (если статус успешно изменен и параметры заданы)
    if success and notify_recipient_role and notify_message_template and rental:  # Убедимся, что rental не None
        recipient_id = None
        if notify_recipient_role == 'renter':
            recipient_id = rental.renter_id
        elif notify_recipient_role == 'owner':
            recipient_id = rental.owner_id
        elif notify_recipient_role == 'other':
            # Определяем ID другой стороны
            recipient_id = rental.owner_id if current_user_role == 'renter' else rental.renter_id

        if recipient_id and recipient_id != user_id:  # Не отправляем уведомление самому себе
            # Получаем имя товара для уведомления
            item_name = None
            try:
                item = ItemRepository.get_item_by_id(db, rental.item_id)
                if item: item_name = item.name
            except Exception as item_err:
                logger.error(
                    f"Не удалось получить имя товара {rental.item_id} для уведомления по аренде {rental_id}: {item_err}")

            # Отправляем уведомление
            RentalService._send_rental_notification(
                db=db,
                rental_id=rental_id,
                recipient_id=recipient_id,
                message_template=notify_message_template,
                item_name=item_name,
                button_text=notify_button_text,
                button_callback_action=notify_button_callback_action
            )
        else:
            logger.debug(
                f"Уведомление по аренде {rental_id} не отправлено (получатель: {recipient_id}, инициатор: {user_id}).")


    @staticmethod
    @with_db_session(commit=True)
    def confirm_rental(rental_id: int, user_id: int, db=None) -> bool:
        ""Владелец подтверждает запрос на аренду.""
        return RentalService._change_rental_status(
            rental_id=rental_id,
            user_id=user_id,
            allowed_roles=["owner"],
            allowed_current_statuses=[RentalStatus.REQUESTED],
            new_status=RentalStatus.CONFIRMED,
            action_name="confirm_rental",
            notify_recipient_role='renter',
            notify_message_template="✅ Ваш запрос на аренду товара {item_name} подтвержден владельцем!",
            notify_button_text="🔍 Посмотреть сделку"
        )

    """

    # Для DISPUTE (оба участника могут, в update_status_if_allowed только 1)
    async def update_status_if_participant(
        self,
        *,
        rental_id: int,
        new_status: RentalStatus,
        expected_status: RentalStatus,
        actor_user_id: int,
    ) -> bool:
        async with self._sf() as s:
            stmt = (
                update(Rental)
                .where(Rental.id == rental_id)
                .where(or_(Rental.owner_id == actor_user_id, Rental.renter_id == actor_user_id))
                .where(Rental.status == expected_status)
                .values(status=new_status)
            )
            res = await s.execute(stmt)
            await s.commit()
            return (res.rowcount or 0) > 0


# ===========================
    # Важно: это не update_status_if_allowed, потому что мы обновляем не статус, а булевый флаг
    # (и ещё защищаемся от повторного клика)

    async def owner_confirm_handover(self, *, rental_id: int, owner_id: int) -> bool:
        """Владелец отмечает: 'передал вещь' (только если CONFIRMED и он owner)"""
        async with self._sf() as s:
            stmt = (
                update(Rental)
                .where(Rental.id == rental_id)
                .where(Rental.owner_id == owner_id)
                .where(Rental.status == RentalStatus.CONFIRMED)
                .where(Rental.owner_handover_confirmed.is_(False))
                .values(owner_handover_confirmed=True) # обновляет поле на True
            )
            res = await s.execute(stmt)
            await s.commit()
            return (res.rowcount or 0) > 0 # True/False (None → 0, 0 → 0, 1 → 1)
            # Была ли реально изменена хотя бы одна строка?
            #   True → изменение произошло (владелец подтвердил передачу)
            #   False → ничего не изменилось

    async def renter_confirm_receive(self, *, rental_id: int, renter_id: int) -> bool:
        """Арендатор отмечает: 'получил вещь' (только если CONFIRMED и он renter)"""
        async with self._sf() as s:
            stmt = (
                update(Rental)
                .where(Rental.id == rental_id)
                .where(Rental.renter_id == renter_id)
                .where(Rental.status == RentalStatus.CONFIRMED)
                .where(Rental.renter_receive_confirmed.is_(False))
                .values(renter_receive_confirmed=True)
            )
            res = await s.execute(stmt)
            await s.commit()
            return (res.rowcount or 0) > 0 # True - арендатор подтвердил получение

    async def activate_if_ready(self, *, rental_id: int) -> bool:
        """CONFIRMED -> ACTIVE если обе стороны подтвердили передачу/получение"""
        async with self._sf() as s:
            stmt = (
                update(Rental)
                .where(Rental.id == rental_id)
                .where(Rental.status == RentalStatus.CONFIRMED)
                .where(Rental.owner_handover_confirmed.is_(True)) # Владелец передал вещь
                .where(Rental.renter_receive_confirmed.is_(True)) # Арендатор получил вещь
                .values(status=RentalStatus.ACTIVE)
            )
            res = await s.execute(stmt)
            await s.commit()
            return (res.rowcount or 0) > 0 # True - арендатор подтвердил получение (статус перешёл в ACTIVE)

"""
    async def get_by_user_id_with_filters(
        self,
        user_id: int,
        *,
        as_renter: bool = True, # Включить аренды, где пользователь является арендатором
        as_owner: bool = True, # Включить аренды, где пользователь является владельцем
        status_filter: Optional[List[RentalStatus]] = None, # Список статусов для фильтрации (None - все статусы)
        order_by_creation: bool = True, # Сортировать ли по убыванию даты создания
    ) -> List[Rental]:
        ""Получает список аренд для указанного пользователя (где пользователь арендатор и/или владелец)""
        async with self._sf() as s:
            stmt = select(Rental)

            # Фильтрация по роли
            role_conditions = []
            if as_renter:
                role_conditions.append(Rental.renter_id == user_id)
            if as_owner:
                role_conditions.append(Rental.owner_id == user_id)
            # если as_renter=True, as_owner=True → [Rental.renter_id == 42, Rental.owner_id == 42]

            if role_conditions:
                stmt = stmt.where(or_(*role_conditions))
                ""or_ — для объединения условий через OR
                   * - «раскрывает» список
                то есть если список [A, B] → в SQL превратится в (A OR B), 
                а именно WHERE (renter_id = 42 OR owner_id = 42)""
            else:
                logger.warning(
                    "get_by_user_id_with_filters() — роль не указана, возвращаем пустой список"
                )
                return []

            # Фильтр по статусам
            if status_filter:
                valid_statuses = [status for status in status_filter if isinstance(status, RentalStatus)]
                ""Берём первый элемент → RentalStatus.ACTIVE → он isinstance(..., RentalStatus) → ✅ добавляем.
                Второй элемент → "ошибка" → это str, а не RentalStatus → ❌ пропускаем.
                Третий элемент → RentalStatus.CONFIRMED → ✅ добавляем.""
                if valid_statuses:
                    stmt = stmt.where(Rental.status.in_(valid_statuses))
                    # Rental.status → это колонка status в таблице rentals
                    # То есть мы достаём только те сделки, у которых статус входит в список valid_statuses
                else:
                    logger.warning(
                        "get_by_user_id_with_filters() — передан некорректный статус фильтра"
                    )

            # Сортировка
            if order_by_creation:
                stmt = stmt.order_by(Rental.created_at.desc())
                # .desc() → убывающий порядок (новые записи первыми)

            res = await s.execute(stmt)
            return list(res.scalars().all())
"""

