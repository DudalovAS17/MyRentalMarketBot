from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from services.rental_service import RentalStatus

STATUS_LABELS = {
    RentalStatus.REQUESTED: "Запрос отправлен",
    RentalStatus.CONFIRMED: "Подтверждена (ожидает передачи)",
    RentalStatus.ACTIVE: "Активна (вещь передана)",
    RentalStatus.COMPLETED: "Завершена",
    RentalStatus.CANCELLED_BY_OWNER: "Отменена владельцем",
    RentalStatus.CANCELLED_BY_RENTER: "Отменена арендатором",
    RentalStatus.REJECTED_BY_OWNER: "Отклонена владельцем",
    RentalStatus.REJECTED_BY_RENTER: "Отклонена арендатором",
    RentalStatus.DISPUTED: "⚠️ <b>Спор открыт</b>. Дальнейшие действия по сделке заблокированы до решения",
    RentalStatus.CANCELLED_CONFIRMED_BY_OWNER: "Отменена владельцем (до передачи)",
    RentalStatus.CANCELLED_CONFIRMED_BY_RENTER: "Отменена арендатором (до получения)",
}


def build_rental_details_ui(details: dict) -> tuple[str, InlineKeyboardMarkup]:
    """
    Собирает текст + клавиатуру для экрана "Детали сделки".
    Никаких БД/сервисов/Telegram-отправки — только UI.
    """

    rental_id = details["id"]
    item = details["item"]
    renter = details["renter"]
    owner = details["owner"]
    status: RentalStatus = details["status"]
    role = details["current_user_role"]  # "owner" | "renter"

    owner_ok = bool(details.get("owner_handover_confirmed"))
    renter_ok = bool(details.get("renter_receive_confirmed"))

    owner_flag = "✅" if owner_ok else "⏳"
    #owner_flag = "✅" if details["owner_handover_confirmed"] else "⏳"
    renter_flag = "✅" if renter_ok else "⏳"
    #renter_flag = "✅" if details["renter_receive_confirmed"] else "⏳"

    # Красивое имя вида: "Александр С. (@potch)"
    def fmt_person(p: dict) -> str:
        name = p.get("full_name") or "—"
        username = p.get("username")
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

    status_text = STATUS_LABELS.get(status, status.value)

    text = (
        f"🔎 <b>Детали сделки #{rental_id}</b>\n\n"
        f"📦 <b>Товар:</b> {item.get('title', '—')}\n"
        # f"<b>Описание</b>: {item.get('description', '—')[:100]???}...\n" # Можно добавить краткое описание
        f"💰 <b>Цена аренды:</b> {item.get('price', 0)} ₽/день\n"
        f"🛡 <b>Залог:</b> {item.get('deposit', 0)} ₽\n\n" # 'Нет'

        f"<b>Стороны:</b>\n"
        f"👤 <b>Арендатор:</b> {fmt_person(renter)}\n"
        f"👑 <b>Владелец:</b> {fmt_person(owner)}\n\n"

        f"<b>Период аренды:</b>\n"
        f"📅 Начало: <b>{details['start_date']:%d.%m.%Y}</b>\n"
        f"📅 Конец: <b>{details['end_date']:%d.%m.%Y}</b>\n\n"

        f"<b>Оплата:</b>\n"
        f"💵 Итого: <b>{details['total_price']} ₽</b>\n\n"

        f"<b>Статус сделки:</b> <b>{status_text}</b>\n" # {status.value}
        
        f"\n<b>Подтверждения:</b>\n"
        f"👑 Владелец передал: {owner_flag}\n"
        f"👤 Арендатор получил: {renter_flag}\n"
    )

    # кнопки
    rows = []

    if role == "owner":
        rows.extend(_build_owner_actions(status, rental_id, owner_ok, renter_ok))
    else:
        rows.extend(_build_renter_actions(status, rental_id, owner_ok, renter_ok))

    rows.append([InlineKeyboardButton(text="🔙 Назад к списку сделок", callback_data="rental_list")])
    # back_to_rentals

    return text, InlineKeyboardMarkup(inline_keyboard=rows)


def _build_owner_actions(status: RentalStatus, rental_id: int, owner_ok: bool, renter_ok: bool) -> list[list[InlineKeyboardButton]]:
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

    return rows


def _build_renter_actions(status: RentalStatus, rental_id: int, owner_ok: bool, renter_ok: bool) -> list[list[InlineKeyboardButton]]:
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

    return rows