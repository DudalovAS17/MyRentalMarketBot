from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from status.item_status import ItemStatus
from status.rental_status import RentalStatus
from status.user_status import AccountStatus
from status.support_ticket_status import SupportTicketStatus
from schemas.rental import RentalAdminDetailsOut
from utils.callbacks import ADMIN_ADD_ITEM_CB

def get_admin_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📄 Заявки на аренду", callback_data="admin:deals"),
                InlineKeyboardButton(text="📦 Модерация объявлений", callback_data="admin:items"),
            ],
            [
                InlineKeyboardButton(text="👥 Управление пользователями", callback_data="admin:users"),
                InlineKeyboardButton(text="➕ Создать объявление", callback_data=ADMIN_ADD_ITEM_CB),
            ],
            [
                InlineKeyboardButton(text="🆘 Поддержка", callback_data="admin:support"),
                InlineKeyboardButton(text="📚 Контент/FAQ", callback_data="admin:content"),
            ],
            [
                InlineKeyboardButton(text="🔙 Назад в меню", callback_data="admin:exit"),
            ],
            # 📊 Статистика,
            # 📢 Рассылка сообщений,
            # ⚙️ Настройки бота
        ]
    )

def get_back_to_admin_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад в админ-меню", callback_data="admin:menu")]
        ]
    )


# ────────────────────────────────────────────────── ADMIN ITEMS ───────────────────────────────────────────────────────
def get_admin_items_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🟡 PENDING", callback_data="admin:items:filter:PENDING")],
            [InlineKeyboardButton(text="✅ ACTIVE", callback_data="admin:items:filter:ACTIVE")],
            [InlineKeyboardButton(text="🙈 HIDDEN", callback_data="admin:items:filter:HIDDEN")],
            [InlineKeyboardButton(text="🔙 Назад в админ-меню", callback_data="admin:menu")],
        ]
    )

def get_admin_items_list_keyboard(items: list, status: str, page: int, has_next: bool) -> InlineKeyboardMarkup: # status: ItemStatus
    kb = []

    for item in items:
        kb.append(
            [InlineKeyboardButton(text=f"🔎 Открыть #{item.id}", callback_data=f"admin:items:view:{item.id}")]
        )

    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton(text="⬅️ Пред", callback_data=f"admin:items:page:{status}:{page-1}"))
    if has_next:
        nav.append(InlineKeyboardButton(text="➡️ След", callback_data=f"admin:items:page:{status}:{page+1}"))
    if nav:
        kb.append(nav)

    #kb.append([InlineKeyboardButton(text="🔙 Назад в админ-меню", callback_data="admin:menu")])
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin:items")])

    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_admin_item_details_keyboard(item_id: int, status_value: ItemStatus) -> InlineKeyboardMarkup:
    kb = []
    kb.append([InlineKeyboardButton(text="🔄 Обновить", callback_data=f"admin:items:view:{item_id}")])

    if status_value == ItemStatus.PENDING:
        kb.append([InlineKeyboardButton(text="✅ Сделать ACTIVE", callback_data=f"admin:items:approve:{item_id}")])
        kb.append([InlineKeyboardButton(text="❌ Reject", callback_data=f"admin:items:reject:{item_id}")])
    if status_value == ItemStatus.ACTIVE:
        kb.append([InlineKeyboardButton(text="🙈 Hide", callback_data=f"admin:items:hide:{item_id}")])
    if status_value == ItemStatus.HIDDEN:
        kb.append([InlineKeyboardButton(text="👁️ Unhide", callback_data=f"admin:items:unhide:{item_id}")])

    kb.append([InlineKeyboardButton(text="🔙 К списку", callback_data="admin:items")])

    return InlineKeyboardMarkup(inline_keyboard=kb)


# ────────────────────────────────────────────────── ADMIN USERS ───────────────────────────────────────────────────────
def get_admin_users_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔎 Найти по user_id", callback_data="admin:users:find")],
            [InlineKeyboardButton(text="🔙 Назад в админ-меню", callback_data="admin:menu")],
        ]
    )

def get_admin_user_card_keyboard(user_id: int, account_status: AccountStatus) -> InlineKeyboardMarkup:
    kb = []

    if account_status == AccountStatus.ACTIVE:
        kb.append([InlineKeyboardButton(text="🚫 Ban", callback_data=f"admin:users:ban:{user_id}")])
    elif account_status == AccountStatus.BANNED:
        kb.append([InlineKeyboardButton(text="✅ Unban", callback_data=f"admin:users:unban:{user_id}")])

    kb.append([InlineKeyboardButton(text="🔄 Обновить", callback_data=f"admin:users:view:{user_id}")])
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin:users")])

    return InlineKeyboardMarkup(inline_keyboard=kb)


# ────────────────────────────────────────────────── ADMIN DEALS ───────────────────────────────────────────────────────
def get_admin_deals_list_keyboard(rentals_rows: list[RentalAdminDetailsOut], page: int, has_next: bool) -> InlineKeyboardMarkup:
    kb = []

    for row in rentals_rows:
        r = row.rental
        kb.append(
            [InlineKeyboardButton(text=f"🔎 Открыть #{r.id}", callback_data=f"admin:deals:view:{r.id}")]
        )

    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton(text="⬅️ Пред", callback_data=f"admin:deals:page:{page-1}"))
    if has_next:
        nav.append(InlineKeyboardButton(text="➡️ След", callback_data=f"admin:deals:page:{page+1}"))
    if nav:
        kb.append(nav)

    kb.append([InlineKeyboardButton(text="🔎 Открыть по ID", callback_data="admin:deals:by_id")])
    kb.append([InlineKeyboardButton(text="🔙 Назад в админ-меню", callback_data="admin:menu")])

    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_admin_deal_details_keyboard(rental_id: int, status: RentalStatus) -> InlineKeyboardMarkup:
    kb = []

    kb.append([InlineKeyboardButton(text="🔄 Обновить", callback_data=f"admin:deals:view:{rental_id}")])

    if status == RentalStatus.REQUESTED:
        kb.append([InlineKeyboardButton(text="👀 Взять в работу", callback_data=f"admin:deals:progress:{rental_id}")])

    if status in {RentalStatus.REQUESTED, RentalStatus.IN_PROGRESS}:
        kb.append([InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"admin:deals:confirm:{rental_id}")])
        kb.append([InlineKeyboardButton(text="❌ Отклонить", callback_data=f"admin:deals:reject:{rental_id}")])

    if status == RentalStatus.CONFIRMED:
        kb.append([InlineKeyboardButton(text="🚫 Отменить", callback_data=f"admin:deals:cancel:{rental_id}")]) # "🚫 Отменить сделку"
        kb.append([InlineKeyboardButton(text="🏁 Завершить", callback_data=f"admin:deals:complete:{rental_id}")])

    # # Кнопка “закрыть спор” только если статус disputed
    # if status == RentalStatus.DISPUTED:
    #     kb.append([InlineKeyboardButton(text="✅ Закрыть спор", callback_data=f"admin:deals:resolve:{rental_id}")])

    kb.append([InlineKeyboardButton(text="🔙 К списку", callback_data="admin:deals")])

    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_admin_dispute_target_keyboard(rental_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➡️ Перевести в ACTIVE", callback_data=f"admin:deals:resolve_target:{rental_id}:active")],
            [InlineKeyboardButton(text="✅ Завершить (COMPLETED)", callback_data=f"admin:deals:resolve_target:{rental_id}:completed")],
            [InlineKeyboardButton(text="↩️ Вернуть в CONFIRMED", callback_data=f"admin:deals:resolve_target:{rental_id}:confirmed")],
            [InlineKeyboardButton(text="🔙 Отмена", callback_data=f"admin:deals:view:{rental_id}")],
        ]
    )


# ───────────────────────────────────────────────── ADMIN SUPPORT ──────────────────────────────────────────────────────
def get_admin_support_list_keyboard(tickets_rows: list[dict], page: int, has_next: bool) -> InlineKeyboardMarkup:
    kb = []

    for row in tickets_rows:
        ticket = row["ticket"]
        kb.append(
            [InlineKeyboardButton(text=f"🎫 Открыть Тикет #{ticket.id}", callback_data=f"admin:support:view:{ticket.id}")]
        )

    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton(text="⬅️ Пред", callback_data=f"admin:support:page:{page-1}"))
    if has_next:
        nav.append(InlineKeyboardButton(text="➡️ След", callback_data=f"admin:support:page:{page+1}"))
    if nav:
        kb.append(nav)

    kb.append([InlineKeyboardButton(text="🔙 Назад в админ-меню", callback_data="admin:menu")]) # admin:support
    return InlineKeyboardMarkup(inline_keyboard=kb)
#get_admin_support_list_kb

def get_admin_support_ticket_keyboard(ticket_id: int, status: SupportTicketStatus) -> InlineKeyboardMarkup:
    kb = []
    kb.append([InlineKeyboardButton(text="🔄 Обновить", callback_data=f"admin:support:view:{ticket_id}")])

    if status == SupportTicketStatus.OPEN:
        kb.append([InlineKeyboardButton(text="✉️ Ответить", callback_data=f"admin:support:reply:{ticket_id}")])
        kb.append([InlineKeyboardButton(text="✅ Закрыть", callback_data=f"admin:support:close:{ticket_id}")])

    kb.append([InlineKeyboardButton(text="🔙 К списку", callback_data="admin:support")])
    return InlineKeyboardMarkup(inline_keyboard=kb)


def get_admin_support_ticket_notification_keyboard(ticket_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔎 Открыть", callback_data=f"admin:support:view:{ticket_id}"),
                InlineKeyboardButton(text="✉️ Ответить", callback_data=f"admin:support:reply:{ticket_id}"),
                InlineKeyboardButton(text="✅ Закрыть", callback_data=f"admin:support:close:{ticket_id}"),
                #[InlineKeyboardButton(text="🔙 К списку", callback_data="admin:support:open")]
            ]
        ]
    )
# get_admin_ticket_kb

def get_admin_support_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📭 Открытые тикеты", callback_data="admin:support:open")],
            [InlineKeyboardButton(text="🔙 Назад в админ-меню", callback_data="admin:menu")],
        ]
    )