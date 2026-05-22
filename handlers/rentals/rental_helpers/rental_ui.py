from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from services.rental_service import RentalStatus
from status.rental_status import RentalActorRole, STATUS_LABELS
from schemas.rental import RentalDetailsOut
from utils.ui_defaults import ui_str, ui_money


def format_rental_status(status: RentalStatus) -> str:
    return status.value.replace("_", " ").replace("-", " ").capitalize()

def build_rental_details_ui(details: RentalDetailsOut) -> tuple[str, InlineKeyboardMarkup]:
    """
    Собирает текст + клавиатуру для экрана "Детали сделки".
    Никаких БД/сервисов/Telegram-отправки — только UI.
    """
    rental_id = details.id
    rental = details.rental
    item = details.item
    renter = details.renter
    owner = details.owner
    user_role = details.user_role

    # Было: getattr(item, "title", "Неизвестный товар")
    item_title = ui_str(getattr(item, "title", None), "Неизвестный товар")
    # getattr(item, "description", "-")
    item_desc = ui_str(getattr(item, "description", None), "-") # [:100]???
    # getattr(item, "location", "-")
    item_location = ui_str(getattr(item, "location", None), "-")

    # getattr(item, "price", 0)
    item_price = ui_money(getattr(item, "price", None), "0")
    # deposit": getattr(item, "deposit", 0)
    item_deposit = ui_money(getattr(item, "deposit", None), "0") # 'Нет'

    # "full_name": renter.full_name if renter else "Неизвестный арендатор",
    renter_name = ui_str(getattr(renter, "full_name", None), "Неизвестный арендатор")
    # owner.full_name if owner else "Неизвестный владелец"
    owner_name = ui_str(getattr(owner, "full_name", None), "Неизвестный владелец")

    """ 
    "item": {
        "id": item.id if item else None,
        # "photos": getattr(item, "photos", []), # !!! Фото лучше тянуть через PhotoService/Repository.
    }
    owner": {
            "id": owner.id if owner else None,
            "username": owner.username if owner else None,
            "phone": owner.phone if owner else None,
    }
    """

    owner_ok = bool(rental.owner_handover_confirmed)
    renter_ok = bool(rental.renter_receive_confirmed)
    owner_flag = "✅" if owner_ok else "⏳"
    renter_flag = "✅" if renter_ok else "⏳"

    renter_username = renter.username
    owner_username = owner.username
    # Красивое имя вида: "Александр С. (@potch)"
    def fmt_person(name: str, username: str = None) -> str:
        return f"{name} (@{username})" if username else name

    """
    # 2️⃣ Показывать ли контакты?
    show_contacts = status in ("confirmed", "active") # [RentalStatus.CONFIRMED, RentalStatus.ACTIVE]
    
    def format_contact(user: dict) -> str:
        ""Форматирует контакт пользователя:
        - всегда показывает @username, если есть
        - телефон показывает только если разрешено
        ""
        if user.get("username"):
            return f" (@{user['username']})"

        if show_contacts and user.get("phone_number"):
            return f" ({user['phone_number']})"

        return ""

    renter_contact = format_contact(renter)
    owner_contact = format_contact(owner)
    """

    status: RentalStatus = rental.status
    status_text = STATUS_LABELS.get(status, status.value)

    #status_display = format_rental_status(status)

    text = (
        f"🔎 <b>Детали сделки #{rental_id}</b>\n\n"
        f"📦 <b>Товар:</b> {item_title}\n"
        f"<b>Описание</b>: {item_desc}\n" # }...\n" (если сделаю логику [:100])
        f"💰 <b>Цена аренды:</b> {item_price} ₽/день\n"
        f"🛡 <b>Залог:</b> {item_deposit} ₽\n\n"

        f"<b>Стороны:</b>\n"
        f"👤 <b>Арендатор:</b> {fmt_person(renter_name, renter_username)}\n"
        f"👑 <b>Владелец:</b> {fmt_person(owner_name, renter_username)}\n\n"

        f"<b>Период аренды:</b>\n"
        f"📅 Начало: <b>{rental.start_date:%d.%m.%Y}</b>\n"
        f"📅 Конец: <b>{rental.end_date:%d.%m.%Y}</b>\n\n"

        f"<b>Оплата:</b>\n"
        f"💵 Итого: <b>{item_price} ₽</b>\n\n"

        f"<b>Статус сделки:</b> <b>{status_text}</b>\n" # {status.value}
        
        f"\n<b>Подтверждения:</b>\n"
        f"👑 Владелец передал: {owner_flag}\n"
        f"👤 Арендатор получил: {renter_flag}\n"
    )

    # кнопки
    rows = []

    if user_role == RentalActorRole.OWNER:
        rows.extend(build_owner_actions(status, rental_id, owner_ok, renter_ok))
    else:
        rows.extend(build_renter_actions(status, rental_id, owner_ok, renter_ok))

    rows.append([InlineKeyboardButton(text="🔙 Назад к списку сделок", callback_data="rental_list")])
    # back_to_rentals

    return text, InlineKeyboardMarkup(inline_keyboard=rows)


def build_owner_actions(status: RentalStatus, rental_id: int, owner_ok: bool, renter_ok: bool) -> list[list[InlineKeyboardButton]]:
    rows = []

    if status == RentalStatus.REQUESTED:
        rows.append([InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"rental_action:confirm:{rental_id}")])
        rows.append([InlineKeyboardButton(text="❌ Отклонить", callback_data=f"rental_action:rejected_by_owner:{rental_id}")])

    elif status == RentalStatus.CONFIRMED:
        # дальше можно: "перевести в ACTIVE" или "отменить владельцем"
        rows.append([InlineKeyboardButton(text="❌ Отменить аренду", callback_data=f"rental_action:cancelled_confirmed_by_owner:{rental_id}")])

        # ключевая логика:
        if owner_ok:
            rows.append([InlineKeyboardButton(text="✅ Передача подтверждена", callback_data="ignore")])
        else:
            rows.append([InlineKeyboardButton(text="📦 Передал вещь",
                                              callback_data=f"rental_action:handover_owner:{rental_id}")])

        # ключевая логика:
        #if not owner_handover_confirmed:
        #    rows.append([InlineKeyboardButton(text="📦 Передал вещь", callback_data=f"rental_action:handover_owner:{rental_id}")])

    elif status == RentalStatus.ACTIVE:
        rows.append([InlineKeyboardButton(text="✅ Завершить", callback_data=f"rental_action:complete:{rental_id}")])
        rows.append([InlineKeyboardButton(text="⚠️ Открыть спор", callback_data=f"rental_action:dispute:{rental_id}")])
        rows.append([InlineKeyboardButton(text="❌ Отменить активную аренду", callback_data=f"rental_action:cancelled_by_owner:{rental_id}")])

    #elif status == RentalStatus.CANCELLED_CONFIRMED_BY_OWNER:
        # обрабатывается отсутствием кнопок

    elif status == RentalStatus.DISPUTED: # пока из Спора нельзя выйти - делает админ
        rows.append([InlineKeyboardButton(text="💬 Написать в поддержку", callback_data=f"support_chat:{rental_id}")])
        return rows # исключаем другие кнопки

    elif status == RentalStatus.COMPLETED:
        #  if details.get("can_leave_review", True):
        #         rows.append([InlineKeyboardButton(text="⭐ Оставить отзыв", callback_data=f"review_start:{rental_id}")])
        #     else:
        #         rows.append([InlineKeyboardButton(text="⭐ Посмотреть отзыв", callback_data=f"review_view:{rental_id}")])
        InlineKeyboardButton(text="⭐ Оставить отзыв", callback_data=f"rental_action:review:{rental_id}")
        # можно ли открыть спор после COMPLETED? Пока нет!
        # ?
        #rows.append([InlineKeyboardButton(text="⭐ Оставить отзыв", callback_data=f"rental_action:review:{rental_id}")])

    return rows


def build_renter_actions(status: RentalStatus, rental_id: int, owner_ok: bool, renter_ok: bool) -> list[list[InlineKeyboardButton]]:
    rows = []

    if status == RentalStatus.REQUESTED:
        rows.append([InlineKeyboardButton(text="❌ Отменить запрос", callback_data=f"rental_action:rejected_by__renter:{rental_id}")])

    elif status == RentalStatus.CONFIRMED:
        rows.append([InlineKeyboardButton(text="❌ Отменить аренду", callback_data=f"rental_action:cancelled_confirmed_by_renter:{rental_id}")])

        # ключевая логика:
        if not renter_ok:
            rows.append([InlineKeyboardButton(text="📦 Получил вещь", callback_data=f"rental_action:receive_renter:{rental_id}")])

    elif status == RentalStatus.ACTIVE:
        rows.append([InlineKeyboardButton(text="⚠️ Открыть спор", callback_data=f"rental_action:dispute:{rental_id}")])
        rows.append([InlineKeyboardButton(text="❌ Отменить активную аренду", callback_data=f"rental_action:cancelled_by_renter:{rental_id}")])

    #elif status == RentalStatus.CANCELLED_CONFIRMED_BY_RENTER:
        # обрабатывается отсутствием кнопок

    elif status == RentalStatus.DISPUTED:
        rows.append([InlineKeyboardButton(text="💬 Написать в поддержку", callback_data=f"support_chat:{rental_id}")])
        return rows # исключаем другие кнопки

    elif status == RentalStatus.COMPLETED:
        #  if details.get("can_leave_review", True):
        #         rows.append([InlineKeyboardButton(text="⭐ Оставить отзыв", callback_data=f"review_start:{rental_id}")])
        #     else:
        #         rows.append([InlineKeyboardButton(text="⭐ Посмотреть отзыв", callback_data=f"review_view:{rental_id}")])
        InlineKeyboardButton(text="⭐ Оставить отзыв", callback_data=f"rental_action:review:{rental_id}")
        # можно ли открыть спор после COMPLETED? Пока нет!

        # ?
        # rows.append([InlineKeyboardButton(text="⭐ Оставить отзыв", callback_data=f"rental_action:review:{rental_id}")])

    return rows