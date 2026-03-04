# САМА СДЕЛКА МЕЖДУ ВЛАДЕЛЬЦЕМ И АРЕНДАТОРОМ
import logging
from aiogram import F
from aiogram.types import CallbackQuery

from .router import rental_router
from .details import render_rental_details
from services.rental_service import RentalService
from utils.errors import ServiceError

logger = logging.getLogger(__name__)


"""
Сделка всегда находится в одном статусе.
Переходы строго ограничены.

Никаких «если захотели — поменяли».

1. REQUESTED — «Запрос отправлен» (кто создает: арендатор - нажал «🤝 Арендовать»)

Что видит арендатор:
        Статус: ⏳ Ожидает подтверждения
        Кнопка: ❌ Отменить запрос

Что видит владелец:
        Новый запрос аренды
        Кнопки:
            ✅ Подтвердить
            ❌ Отклонить

Кто	   → Действие
OWNER  → CONFIRMED
OWNER  → REJECTED
RENTER → CANCELLED_BY_RENTER
-------------------------------------------

2. Переход: REQUESTED → CONFIRMED — «Подтверждено владельцем» (кто переводит: владелец)

Что видят оба:
        Даты аренды
        Контакт друг друга
        Статус: 🟢 Подтверждено
Кнопки:
    RENTER: ❌ Отменить (до начала)
    OWNER: ❌ Отменить (до начала)

Владелец согласился - Вещь «зарезервирована»
!Но что важно: Аренда еще не началась, это ожидание даты, т.е. перехода SYSTEM → ACTIVE
(начать аренду - сам бот автоматически)
-------------------------------------------

3. ACTIVE — «Аренда активна»
Переход: CONFIRMED → ACTIVE (Кто переводит: SYSTEM)
1) CONFIRMED: Владелец согласился (юридически/логически вы договорились)
2) ACTIVE: Фактическое пользование вещью началось (вещь передана, время пошло, депозит/оплата применились)

ACTIVE = “аренда идёт, вещь у арендатора, период считается, правила отмены/спора другие”

Чтобы ACTIVE означал реальный факт передачи, нам нужна “двухсторонняя фиксация”:
    владелец нажал «Передал вещь»
    арендатор нажал «Получил вещь»
    только когда оба события произошли → переводим в ACTIVE

В ACTIVE меняется всё:
    появляются основания для спора,
    отмена превращается в “разрыв активной аренды” (другие последствия),
    начинается (или считается) срок,
    можно “завершить” только после факта возврата.

Что видят оба:
    Статус: 🔵 Активна
    Дата окончания
Кнопки:
    🆘 Открыть спор (Сообщить о проблеме) 
    ❌ Досрочно завершить (опционально) - оба или только Владелец?

Переходы:
SYSTEM → COMPLETED (по end_date)
RENTER/OWNER → DISPUTED
-------------------------------------------

🟣 4. COMPLETED — «Завершена» (Кто переводит: SYSTEM \или\ OWNER подтвердил возврат)
Переход: ACTIVE → COMPLETED

Вещь возвращена
Финансы зафиксированы
Можно оставлять отзыв (👉 ТОЛЬКО здесь появляются отзывы)

Что видят оба:
    Статус: ✅ Завершена
    Кнопка: ⭐ Оставить отзыв (если не оставлен)
Переходы:
    нет (ФИНАЛ)
-------------------------------------------

🔴 5. REJECTED — «Отклонена» (кем: владельцем)
Переход: REQUESTED → REJECTED
Финал. Отзывов нет.

ЛИБО
⚫ 5.1. CANCELLED_BY_RENTER — «Отменено арендатором»
Переходы:
REQUESTED → CANCELLED_BY_RENTER
CONFIRMED → CANCELLED_BY_RENTER
ACTIVE → CANCELLED_BY_RENTER (опционально)

⚫ 5.2. CANCELLED_BY_OWNER — «Отменено владельцем»
Переходы:
REQUESTED → CANCELLED_BY_OWNER
CONFIRMED → CANCELLED_BY_OWNER
ACTIVE → CANCELLED_BY_OWNER (опционально)


⚠️ 8. DISPUTED — «Спор» (Кто: любой участник)
Когда: проблема во время ACTIVE

Что дальше:
    ручная обработка
    админ
    заморозка денег
"""

def _parse_rental_id(callback: CallbackQuery) -> int | None:
    """Ожидаем формат callback_data: rental_action:<action>:<rental_id>

    Возвращает rental_id или None"""

    try: # ожидаем жёсткий формат: ["rental_action", "confirm", "<id>"] - rental_action:confirm:<id>
        parts = callback.data.split(":") # action = parts[1]
        return int(parts[2])
    except (IndexError, ValueError):
        return None

async def _run_rental_action(
        *,
        callback: CallbackQuery,
        rental_service,
        user,
        rental_id: int,
        service_call, # awaitable -> bool
        # rental_service.confirm_requested(rental_id=rental_id, actor_id=user.id)
        ok_text: str, # "Подтверждено" из await callback.answer()
        fail_text: str, # fail_text = "Не удалось подтвердить (статус уже изменился или нет прав)."
        # log_name: str, # по сути название функции, чтобы в лог вставить
) -> None:
    """
    Единая обвязка для действий над сделкой (atomic transition).

    - выполняет сервис-метод
    - обрабатывает исключения
    - показывает callback.answer()
    - перерисовывает детали (всегда после fail/ok, кроме crash)

    Типы ситуаций:
    1) Recoverable (business отказ): ok=False
       → alert fail_text + refresh UI (по умолчанию да)

    2) Recoverable (infra): ServiceError
       → alert "Попробуйте позже" + return (без refresh)
       (мы не уверены, изменился ли статус)

    3) Fatal (infra crash): Exception
       → logger.exception + alert "Ошибка" + return (без refresh)
       (то же: не уверены в консистентности)
    """

    # Вызов бизнес-логики: “Попробуй перевести сделку в STATUS, если это разрешено”
    try:
        ok = await service_call()
    except ServiceError:
        # Recoverable-infra: БД/тайм-аут/сервис недоступен (НЕ бизнес-логика)
        await callback.answer("Ошибка. Попробуйте позже.", show_alert=True)
        return
    # Почему return сразу: мы не знаем, изменился ли статус / UI может стать ложным / нельзя продолжать
    # Тут НЕ должно быть render_rental_details"""

    # Recoverable-business: Бизнес-отказ (статус уже не REQUESTED | пользователь не владелец | другой пользователь успел раньше)
    if not ok:
        await callback.answer(fail_text, show_alert=True)
        # Почему здесь show_alert=True: пользователь ожидал действие → нужно явно объяснить, почему “не сработало”

        await render_rental_details(callback, rental_service, user, rental_id)
        # даже при fail — перерисуем, чтобы UI был актуальным и пользователь должен увидеть новый статус/новые кнопки
        return

    # Успешный сценарий
    await callback.answer(ok_text)

    # Перерисовка после успеха
    await render_rental_details(callback, rental_service, user, rental_id)

"""Эта функция и + _parse_rental_id():
    ✅ корректно обрабатывает все 3 типа ошибок
    ✅ не смешивает бизнес и инфраструктуру
    ✅ всегда приводит UI в актуальное состояние
"""

@rental_router.callback_query(F.data.startswith("rental_action:confirm:"))
async def rental_confirm(callback: CallbackQuery, rental_service, user):
    """Кнопка владельца “Подтвердить” (REQUESTED → CONFIRMED)"""

    rental_id = _parse_rental_id(callback)

    if rental_id is None: # Fatal (input): некорректная кнопка → нельзя звать сервис/перерисовывать UI
        await callback.answer("Некорректная кнопка.", show_alert=True)
        return

    await _run_rental_action(
        callback=callback,
        rental_service=rental_service,
        user=user,
        rental_id=rental_id,
        service_call=lambda: rental_service.confirm_requested(rental_id=rental_id, actor_id=user.id),
        ok_text="Подтверждено",
        fail_text="Не удалось подтвердить (статус изменился или нет прав).",
        # log_name="confirm_requested",
    )
    # confirm_requested() внутри: проверяет: существует ли сделка / является ли пользователь владельцем /
    # статус = REQUESTED / делает атомарный update / возвращает True-False"""

# Владелец отклонил запрос аренды
@rental_router.callback_query(F.data.startswith("rental_action:rejected_by_owner:"))
async def rental_reject_by_owner(callback: CallbackQuery, rental_service: RentalService, user):
    """Кнопка владельца “❌ Отклонить” (REQUESTED → REJECTED_BY_OWNER)"""

    rental_id = _parse_rental_id(callback)
    if rental_id is None:
        await callback.answer("Некорректная кнопка.", show_alert=True)
        return

    await _run_rental_action(
        callback=callback,
        rental_service=rental_service,
        user=user,
        rental_id=rental_id,
        service_call=lambda: rental_service.reject_requested_by_owner(rental_id=rental_id, owner_id=user.id),
        ok_text="Отклонено",
        fail_text="Не удалось отклонить (статус изменился или нет прав).",
        # log_name="reject_requested_by_owner",
    )

# Арендатор отклонил свой запрос аренды
@rental_router.callback_query(F.data.startswith("rental_action:rejected_by_renter:"))
async def rental_reject_by_renter(callback: CallbackQuery, rental_service: RentalService, user):
    """Кнопка арендатора “❌ Отклонить” (REQUESTED → REJECTED_BY_RENTER)"""

    rental_id = _parse_rental_id(callback)
    if rental_id is None:
        await callback.answer("Некорректная кнопка.", show_alert=True)
        return

    await _run_rental_action(
        callback=callback,
        rental_service=rental_service,
        user=user,
        rental_id=rental_id,
        service_call=lambda: rental_service.reject_requested_by_renter(rental_id=rental_id, renter_id=user.id),
        ok_text="Запрос отменён",
        fail_text="Не удалось отменить (статус изменился или нет прав).",
        # log_name="reject_requested_by_renter",
    )

# Владелец отменяет подтвержденную аренду
@rental_router.callback_query(F.data.startswith("rental_action:cancelled_confirmed_by_owner:"))
async def rental_cancel_confirmed_by_owner(callback: CallbackQuery, rental_service: RentalService, user):

    rental_id = _parse_rental_id(callback)
    if rental_id is None:
        await callback.answer("Некорректная кнопка.", show_alert=True)
        return

    await _run_rental_action(
        callback=callback,
        rental_service=rental_service,
        user=user,
        rental_id=rental_id,
        service_call=lambda: rental_service.cancel_confirmed_by_owner(rental_id=rental_id, owner_id=user.id),
        ok_text="Аренда отменена владельцем",
        fail_text="Не удалось отменить (статус изменился или нет прав).",
        # log_name="cancel_confirmed_by_owner",
    )

# Арендатор отменяет подтвержденную аренду
@rental_router.callback_query(F.data.startswith("rental_action:cancelled_confirmed_by_renter:"))
async def rental_cancel_confirmed_by_renter(callback: CallbackQuery, rental_service: RentalService, user):

    rental_id = _parse_rental_id(callback)
    if rental_id is None:
        await callback.answer("Некорректная кнопка.", show_alert=True)
        return

    await _run_rental_action(
        callback=callback,
        rental_service=rental_service,
        user=user,
        rental_id=rental_id,
        service_call=lambda: rental_service.cancel_confirmed_by_renter(rental_id=rental_id, renter_id=user.id),
        ok_text="Аренда отменена арендатором",
        fail_text="Не удалось отменить (статус изменился или нет прав).",
        # log_name="cancel_confirmed_by_renter",
    )

# Владелец отменяет активную аренду
@rental_router.callback_query(F.data.startswith("rental_action:cancelled_by_owner:"))
async def rental_cancel_active_by_owner(callback: CallbackQuery, rental_service: RentalService, user):
    """Владелец отменяет активную аренду"""

    rental_id = _parse_rental_id(callback)
    if rental_id is None:
        await callback.answer("Некорректная кнопка.", show_alert=True)
        return

    await _run_rental_action(
        callback=callback,
        rental_service=rental_service,
        user=user,
        rental_id=rental_id,
        service_call=lambda: rental_service.cancel_active_by_owner(rental_id=rental_id, owner_id=user.id),
        ok_text="Активная аренда отменена владельцем",
        fail_text="Не удалось отменить (статус изменился или нет прав).",
        # log_name="cancel_active_by_owner",
    )

# Арендатор отменяет активную аренду
@rental_router.callback_query(F.data.startswith("rental_action:cancelled_by_renter:"))
async def rental_cancel_active_by_renter(callback: CallbackQuery, rental_service: RentalService, user):
    """Арендатор отменяет активную аренду"""

    rental_id = _parse_rental_id(callback)
    if rental_id is None:
        await callback.answer("Некорректная кнопка.", show_alert=True)
        return

    await _run_rental_action(
        callback=callback,
        rental_service=rental_service,
        user=user,
        rental_id=rental_id,
        service_call=lambda: rental_service.cancel_active_by_renter(rental_id=rental_id, renter_id=user.id),
        ok_text="Активная аренда отменена арендатором",
        fail_text="Не удалось отменить (статус изменился или нет прав).",
        # log_name="cancel_active_by_renter",
    )


# ******************** это не статусы, а булевый флаг ***********
"""
Чтобы ACTIVE означал реальный факт передачи, нам нужна “двухсторонняя фиксация”:
    владелец нажал «Передал вещь»
    арендатор нажал «Получил вещь»
    только когда оба события произошли → переводим в ACTIVE

В ACTIVE меняется всё:
    появляются основания для спора,
    отмена превращается в “разрыв активной аренды” (другие последствия),
    начинается (или считается) срок,
    можно “завершить” только после факта возврата.

Архитектурно правильно: не плодить статусы (типа “owner_handed_over”), а хранить “подтверждения-флаги” 
отдельными полями в самой сделке.

И status желательно передавать как Enum, не как строку (чтобы UI работал типобезопасно):
    status: rental.status (Enum)
    status_value: rental.status.value (если нужно для текста)
"""
# “Передал вещь” (owner)
@rental_router.callback_query(F.data.startswith("rental_action:handover_owner:"))
async def rental_handover_owner(callback: CallbackQuery, rental_service: RentalService, user):

    rental_id = _parse_rental_id(callback)
    if rental_id is None:
        await callback.answer("Некорректная кнопка.", show_alert=True)
        return

    await _run_rental_action(
        callback=callback,
        rental_service=rental_service,
        user=user,
        rental_id=rental_id,
        service_call=lambda: rental_service.confirm_handover_by_owner(rental_id=rental_id, owner_id=user.id),
        ok_text="Отмечено: вещь передана",
        fail_text="Не удалось отметить (статус изменился / нет прав / уже отмечено).",
        # log_name="handover_owner",
    )

# “Получил вещь” (renter)
@rental_router.callback_query(F.data.startswith("rental_action:receive_renter:"))
async def rental_receive_renter(callback: CallbackQuery, rental_service: RentalService, user):

    rental_id = _parse_rental_id(callback)
    if rental_id is None:
        await callback.answer("Некорректная кнопка.", show_alert=True)
        return

    await _run_rental_action(
        callback=callback,
        rental_service=rental_service,
        user=user,
        rental_id=rental_id,
        service_call=lambda: rental_service.confirm_receive_by_renter(rental_id=rental_id, renter_id=user.id),
        ok_text="Отмечено: вещь получена",
        fail_text="Не удалось отметить (статус изменился / нет прав / уже отмечено).",
        # log_name="receive_renter",
    )

# по аналогии нужно будет добавить флаг ОПЛАТЫ
"""
Добавь в модель Rental
    payment_confirmed_at: datetime | None (или payment_status)


(позже) Оплата/холд: ✅/⏳

get_rental_details): (позже) payment_confirmed_at

- добавляешь поле payment_confirmed_at (или status)
- добавляешь кнопку/процесс оплаты в CONFIRMED
- в activate_if_ready добавляешь условие: payment_confirmed_at IS NOT NULL
"""
# **********************************************

# ✅ Завершить (owner)
@rental_router.callback_query(F.data.startswith("rental_action:complete:"))
async def rental_complete(callback: CallbackQuery, rental_service: RentalService, user):

    rental_id = _parse_rental_id(callback)
    if rental_id is None:
        await callback.answer("Некорректная кнопка.", show_alert=True)
        return

    await _run_rental_action(
        callback=callback,
        rental_service=rental_service,
        user=user,
        rental_id=rental_id,
        service_call=lambda: rental_service.complete_active(rental_id=rental_id, owner_id=user.id),
        ok_text="Аренда завершена",
        fail_text="Не удалось завершить (статус изменился или нет прав)",
        # log_name="complete_active",
    )

# ⚠️ Открыть спор (owner/renter)
@rental_router.callback_query(F.data.startswith("rental_action:dispute:"))
async def rental_dispute(callback: CallbackQuery, rental_service: RentalService, user):

    rental_id = _parse_rental_id(callback)
    if rental_id is None:
        await callback.answer("Некорректная кнопка.", show_alert=True)
        return

    await _run_rental_action(
        callback=callback,
        rental_service=rental_service,
        user=user,
        rental_id=rental_id,
        service_call=lambda: rental_service.open_dispute(rental_id=rental_id, actor_id=user.id),
        ok_text="Спор открыт",
        fail_text="Не удалось открыть спор (статус изменился или нет прав)",
        # log_name="open_dispute",
    )