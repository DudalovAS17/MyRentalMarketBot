import logging
from aiogram import F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton

from .router import rental_router

from handlers.rental_ui import build_rental_details_ui

from services.rental_service import RentalService
from utils.functions import send_or_edit
from status.rental_status import RentalActorRole, RentalStatus
from utils.errors import ServiceError

logger = logging.getLogger(__name__)

BACK_TO_MENU_CB = "back_to_main_menu" # "back_to_menu" # "menu:main"
MY_RENTALS_CB = "rental_list" # back_to_rentals
RENTAL_DETAILS_CB = "rental_details:"

@rental_router.message(F.text == "📋 Мои сделки")
@rental_router.callback_query(F.data == MY_RENTALS_CB)
# @rental_router.callback_query(F.data == "back_to_rentals")
async def view_my_rentals(event: Message | CallbackQuery, rental_service: RentalService, user) -> None:
    """Показывает список сделок пользователя (и как OWNER, и как RENTER)"""

    if isinstance(event, CallbackQuery):
        await event.answer()

    # Получаем списки сделок
    try:
        rentals = await rental_service.list_user_rentals(user.id)
    except ServiceError:
        await send_or_edit(event, "⚠️ Не удалось загрузить список сделок. Попробуйте позже.")
        return

    rentals = rentals or []

    # Если сделок нет
    if not rentals:
        text = "📭 У вас пока нет активных или завершённых сделок."
        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data=BACK_TO_MENU_CB)]
            ]
        )
        await send_or_edit(event, text, markup)
        return

    # Формируем текст
    text = "<b>📋 Ваши сделки</b>\n\n Выберите сделку, чтобы открыть детали:"

    # Группируем/сортируем: активные сверху
    active_first = {
        RentalStatus.REQUESTED,
        RentalStatus.CONFIRMED,
        RentalStatus.ACTIVE,
        RentalStatus.DISPUTED,
    }

    def _sort_key(ren):
        status_ = ren.status
        return 0 if status_ in active_first else 1, -ren.id
    """ первая часть:
            0, если статус “активный” (REQUESTED/CONFIRMED/ACTIVE/DISPUTED)
            1, если статус “не активный” (COMPLETED/всякие CANCELLED/REJECTED…)
        ✅ При сортировке 0 идёт раньше 1, значит активные сделки будут сверху.

        вторая часть: -id
            если id = 120 → ключ = -120
            если id = 15 → ключ = -15
        ✅ При сортировке по возрастанию -120 < -15, значит больший id окажется раньше.
        То есть внутри каждой группы ты получаешь самые новые сделки сверху (если id растёт).

        id=10, COMPLETED → (1, -10)
        id=11, REQUESTED → (0, -11)
        id=12, ACTIVE → (0, -12)
        id=13, CANCELLED… → (1, -13)
    """

    rentals_sorted = sorted(rentals, key=_sort_key) # берёт каждый элемент ren из списка rentals, вызывает: _sort_key(ren)


    rows: list[list[InlineKeyboardButton]] = []
    for r in rentals_sorted[:30]:  # MVP-ограничение списка
        # роль относительно текущего пользователя
        role = RentalActorRole.OWNER if r.owner_id == user.id else RentalActorRole.RENTER

        role_label = "Владелец" if role == RentalActorRole.OWNER else "Арендатор"
        # role_label = "Вы сдаёте ⬅️" if role == RentalActorRole.OWNER else "Вы арендуете ➡️"

        status_label = r.status.value # getattr(r.status, "value", str(r.status))

        # item_title = r.item_title or f"Вещь #{r.item_id}"
        # start_date = r.start_date
        # end_date = r.end_date

        # text += (
        #     f"• <b>Сделка #{r.id}</b>\n"
        #     f"  {role_label}\n"
        #     #f"  📅 {start_date:%d.%m.%Y} — {end_date:%d.%m.%Y}\n"
        #     f"  🔖 Статус: <i>{status_label}</i>\n\n"
        # )

        button_text = f"# Сделка {r.id} • {role_label} • {status_label} " # • {item_title}
        rows.append([InlineKeyboardButton(text=button_text[:64], callback_data=f"{RENTAL_DETAILS_CB}{r.id}")])

    rows.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data=BACK_TO_MENU_CB)])
    markup = InlineKeyboardMarkup(inline_keyboard=rows)

    # Ограничиваем длину сообщения, если оно слишком большое
    # if len(text) > 3900:
    #    text = text[:3800] + "\n\n… список обрезан (очень много сделок)."

    await send_or_edit(event, text, markup)


@rental_router.callback_query(F.data.startswith(RENTAL_DETAILS_CB))
async def show_rental_details(callback: CallbackQuery, rental_service: RentalService, user):
    """Отображает детали конкретной аренды."""

    await callback.answer()

    try:
        rental_id = int(callback.data.split(":")[1]) # split(":", 1)
    except (IndexError, ValueError):
        await callback.answer("Некорректная сделка.", show_alert=True)
        return
    # logger.info(f"Пользователь {user.id} запросил детали сделки {rental_id}")

    await render_rental_details(callback, rental_service, user, rental_id)


async def render_rental_details(callback: CallbackQuery, rental_service: RentalService, user, rental_id: int) -> None:
    """ Рендер экрана деталей сделки (по callback rental_details:<id>)"""

    # Получаем детали сделки
    try:
        details = await rental_service.get_rental_details(rental_id=rental_id, current_user_id=user.id)
    except ServiceError:
        # Recoverable: временная ошибка сервиса/БД
        await send_or_edit(callback, "⚠️ Не удалось загрузить детали сделки. Попробуйте позже.")
        return

    if not details:
        # Recoverable: нет доступа/не найдено
        await send_or_edit(callback, "❌ Не удалось загрузить детали сделки или у вас нет доступа.")
        return

    # Формируем кнопки в зависимости от статуса и роли
    text, markup = build_rental_details_ui(details)

    # Пытаемся редактировать сообщение, если нельзя — отправляем новое
    await send_or_edit(callback, text, markup=markup, parse_mode="HTML")

