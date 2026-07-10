from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from status.item_status import ItemStatus
from status.rental_status import RentalStatus
from status.user_status import AccountStatus
from status.support_ticket_status import SupportTicketStatus
from schemas.rental import RentalAdminDetailsOut
from utils.callbacks import (ADMIN_ADD_ITEM_CB, BACK_TO_ADMIN_MENU_CB, ADMIN_SUPPORT, ADMIN_SUPPORT_ITEMS, ADMIN_SUPPORT_RENTALS,
                             ADMIN_EXIT_PREFIX, ADMIN_USERS_MOD, ADMIN_CONTENT, ADMIN_ITEMS_MOD, ADMIN_SUPPORT_GENERAL,
                             DEALS_VIEW_PREFIX, DEALS_PROGRESS_PREFIX, DEALS_CONFIRM_PREFIX, DEALS_REJECT_PREFIX, DEALS_COMMENT_PREFIX,
                             DEALS_NEW_PREFIX, DEALS_ALL_PREFIX, DEALS_CONTACT_PREFIX,  # DEALS_PREFIX,
                             ADMIN_ITEMS_MOD_FIND, ADMIN_ITEMS_MOD_EDIT_QUANTITY, ADMIN_ITEMS_MOD_EDIT_PRICE)

def _button_rows_by_two(buttons: list[InlineKeyboardButton]) -> list[list[InlineKeyboardButton]]:
    """Разложить кнопки по две в строке."""
    return [buttons[index:index + 2] for index in range(0, len(buttons), 2)]

# ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
def get_admin_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🆕 Новые заявки", callback_data=DEALS_NEW_PREFIX),
                InlineKeyboardButton(text="📋 Все заявки", callback_data=DEALS_ALL_PREFIX), # DEALS_PREFIX
            ],
            [
                InlineKeyboardButton(text="👥 Наши клиенты", callback_data=ADMIN_USERS_MOD),
                InlineKeyboardButton(text="🆘 Обращения клиентов", callback_data=ADMIN_SUPPORT),
            ],
            [
                InlineKeyboardButton(text="📦 Модерация товаров", callback_data=ADMIN_ITEMS_MOD),
                InlineKeyboardButton(text="➕ Создать товар", callback_data=ADMIN_ADD_ITEM_CB),
            ],
            [
                InlineKeyboardButton(text="📚 Контент/FAQ", callback_data=ADMIN_CONTENT),
            ],
            [
                InlineKeyboardButton(text="🔙 Назад в меню", callback_data=ADMIN_EXIT_PREFIX),
            ],
            # 📊 Статистика,
            # 📢 Рассылка сообщений,
            # ⚙️ Настройки бота
        ]
    )

def get_back_to_admin_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад в админ-меню", callback_data=BACK_TO_ADMIN_MENU_CB)]
        ]
    )

# ────────────────────────────────────────────────── ADMIN ITEMS ───────────────────────────────────────────────────────
def get_admin_items_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔎 Найти товар", callback_data=ADMIN_ITEMS_MOD_FIND)],
            [InlineKeyboardButton(text="📝 Черновики", callback_data="admin:items:filter:DRAFT")],
            [InlineKeyboardButton(text="✅ Опубликованные товары", callback_data="admin:items:filter:ACTIVE")],
            [InlineKeyboardButton(text="🙈 Скрытые товары", callback_data="admin:items:filter:HIDDEN")],
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

    kb = [[InlineKeyboardButton(text="🔄 Обновить", callback_data=f"admin:items:view:{item_id}")]]

    if status_value == ItemStatus.DRAFT:
        kb.append([InlineKeyboardButton(text="✅ Опубликовать", callback_data=f"admin:items:approve:{item_id}")])
        kb.append([InlineKeyboardButton(text="🙈 Скрыть", callback_data=f"admin:items:hide:{item_id}")])

    if status_value == ItemStatus.ACTIVE:
        kb.append([InlineKeyboardButton(text="🙈 Скрыть", callback_data=f"admin:items:hide:{item_id}")])

    if status_value == ItemStatus.HIDDEN:
        kb.append([InlineKeyboardButton(text="👁️ Вернуть в каталог", callback_data=f"admin:items:unhide:{item_id}")])
        kb.append([InlineKeyboardButton(text="🚫 Убрать в архив", callback_data=f"admin:items:archive:{item_id}")])

    kb.append([InlineKeyboardButton(text="📦 Изменить наличие", callback_data=f"{ADMIN_ITEMS_MOD_EDIT_QUANTITY}{item_id}")])
    kb.append([InlineKeyboardButton(text="💰 Изменить цену", callback_data=f"{ADMIN_ITEMS_MOD_EDIT_PRICE}{item_id}")])

    kb.append([InlineKeyboardButton(text="🔙 К списку действий", callback_data="admin:items")])

    return InlineKeyboardMarkup(inline_keyboard=kb)


# ────────────────────────────────────────────────── ADMIN USERS ───────────────────────────────────────────────────────
def get_admin_users_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔎 Найти клиента по id", callback_data="admin:users:find")],
            [InlineKeyboardButton(text="🔙 Назад в админ-меню", callback_data=BACK_TO_ADMIN_MENU_CB)],
        ]
    )

def get_admin_user_card_keyboard(user_id: int, account_status: AccountStatus) -> InlineKeyboardMarkup:
    kb = []

    if account_status == AccountStatus.ACTIVE:
        kb.append([InlineKeyboardButton(text="🚫 Забанить", callback_data=f"admin:users:ban:{user_id}")])
    elif account_status == AccountStatus.BANNED:
        kb.append([InlineKeyboardButton(text="✅ Разбанить", callback_data=f"admin:users:unban:{user_id}")])

    kb.append([InlineKeyboardButton(text="🔄 Обновить", callback_data=f"admin:users:view:{user_id}")])
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin:users")])

    return InlineKeyboardMarkup(inline_keyboard=kb)


# ────────────────────────────────────────────────── ADMIN DEALS ───────────────────────────────────────────────────────
def get_admin_deals_list_keyboard(rentals_rows: list[RentalAdminDetailsOut], page: int, has_next: bool, *, mode: str = "all") -> InlineKeyboardMarkup:
    kb = []
    for row in rentals_rows:
        r = row.rental
        kb.append(
            [InlineKeyboardButton(text=f"🔎 Открыть #{r.id}", callback_data=f"admin:deals:view:{r.id}")]
        )

    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton(text="⬅️ Пред", callback_data=f"admin:deals:{mode}:page:{page-1}"))
    if has_next:
        nav.append(InlineKeyboardButton(text="➡️ След", callback_data=f"admin:deals:{mode}:page:{page+1}"))
    if nav:
        kb.append(nav)

    if mode == "new":
        kb.append([InlineKeyboardButton(text="📋 Показать все заявки", callback_data=DEALS_ALL_PREFIX)])
    else:
        kb.append([InlineKeyboardButton(text="🆕 Показать только новые", callback_data=DEALS_NEW_PREFIX)])

    kb.append([InlineKeyboardButton(text="🔎 Открыть заявку по ID", callback_data="admin:deals:by_id")])
    kb.append([InlineKeyboardButton(text="🔙 Назад в админ-меню", callback_data=BACK_TO_ADMIN_MENU_CB)])

    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_admin_deal_details_keyboard(rental_id: int, status: RentalStatus) -> InlineKeyboardMarkup:
    buttons = [InlineKeyboardButton(text="🔄 Обновить", callback_data=f"admin:deals:view:{rental_id}")]

    if status == RentalStatus.REQUESTED:
        buttons.append(InlineKeyboardButton(text="✅ Взять в работу", callback_data=f"admin:deals:progress:{rental_id}"))

    if status in {RentalStatus.REQUESTED, RentalStatus.IN_PROGRESS}:
        buttons.append(InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"admin:deals:confirm:{rental_id}"))
        buttons.append(InlineKeyboardButton(text="❌ Отклонить", callback_data=f"admin:deals:reject:{rental_id}"))

    if status == RentalStatus.CONFIRMED:
        buttons.append(InlineKeyboardButton(text="🚫 Отменить", callback_data=f"admin:deals:cancel:{rental_id}")) # "🚫 Отменить заявку"
        buttons.append(InlineKeyboardButton(text="🏁 Завершить", callback_data=f"admin:deals:complete:{rental_id}"))

    buttons.append(InlineKeyboardButton(text="📞 Контакт клиента", callback_data=f"{DEALS_CONTACT_PREFIX}{rental_id}"))
    buttons.append(InlineKeyboardButton(text="📝 Комментарий менеджера", callback_data=f"{DEALS_COMMENT_PREFIX}{rental_id}"))
    buttons.append(InlineKeyboardButton(text="🔙 К списку", callback_data=DEALS_ALL_PREFIX))

    return InlineKeyboardMarkup(inline_keyboard=_button_rows_by_two(buttons))

def get_admin_new_rental_notification_keyboard(rental_id: int) -> InlineKeyboardMarkup:
    """Клавиатура уведомления админам о новой заявке на аренду."""
    buttons = [
        InlineKeyboardButton(text="✅ Взять в работу", callback_data=f"{DEALS_PROGRESS_PREFIX}{rental_id}"),
        InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"{DEALS_CONFIRM_PREFIX}{rental_id}"),
        InlineKeyboardButton(text="❌ Отклонить", callback_data=f"{DEALS_REJECT_PREFIX}{rental_id}"),
    ]

    buttons.extend([
        InlineKeyboardButton(text="📞 Контакт клиента", callback_data=f"{DEALS_CONTACT_PREFIX}{rental_id}"),
        InlineKeyboardButton(text="📝 Комментарий менеджера", callback_data=f"{DEALS_COMMENT_PREFIX}{rental_id}"),
        InlineKeyboardButton(text="🔎 Открыть заявку", callback_data=f"{DEALS_VIEW_PREFIX}{rental_id}"),
    ])

    return InlineKeyboardMarkup(inline_keyboard=_button_rows_by_two(buttons))

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
def get_admin_support_sections_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📦 Вопросы по товарам", callback_data=ADMIN_SUPPORT_ITEMS)],
            [InlineKeyboardButton(text="📄 Вопросы по арендам", callback_data=ADMIN_SUPPORT_RENTALS)],
            [InlineKeyboardButton(text="🆘 Общие обращения", callback_data=ADMIN_SUPPORT_GENERAL)],
            [InlineKeyboardButton(text="🔙 Назад в админ-меню", callback_data=BACK_TO_ADMIN_MENU_CB)],
        ]
    )

def get_admin_support_list_keyboard(tickets_rows: list[dict], page: int, has_next: bool, kind: str) -> InlineKeyboardMarkup:
    kb = []

    for row in tickets_rows:
        ticket = row["ticket"]
        kb.append(
            [InlineKeyboardButton(text=f"🎫 Открыть Тикет #{ticket.id}", callback_data=f"admin:support:view:{ticket.id}")]
        )

    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton(text="⬅️ Пред", callback_data=f"admin:support:page:{kind}:{page-1}"))
    if has_next:
        nav.append(InlineKeyboardButton(text="➡️ След", callback_data=f"admin:support:page:{kind}:{page+1}"))
    if nav:
        kb.append(nav)

    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data=ADMIN_SUPPORT)])
    return InlineKeyboardMarkup(inline_keyboard=kb)
#get_admin_support_list_kb

def get_admin_support_ticket_keyboard(ticket_id: int, status: SupportTicketStatus) -> InlineKeyboardMarkup:
    kb = [[InlineKeyboardButton(text="🔄 Обновить", callback_data=f"admin:support:view:{ticket_id}")]]

    if status == SupportTicketStatus.OPEN:
        kb.append([InlineKeyboardButton(text="✉️ Ответить", callback_data=f"admin:support:reply:{ticket_id}")])
        kb.append([InlineKeyboardButton(text="✅ Закрыть", callback_data=f"admin:support:close:{ticket_id}")])

    kb.append([InlineKeyboardButton(text="🔙 К разделам обращений", callback_data=ADMIN_SUPPORT)])
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
            [InlineKeyboardButton(text="🔙 Назад в админ-меню", callback_data=BACK_TO_ADMIN_MENU_CB)],
        ]
    )


# ───────────────────────────────────────── ADMIN ITEMS (возможное доп-е) ──────────────────────────────────────────────
SHOW_ITEM_CB = "show_item:"
EDIT_ITEM_CB = "edit_item" # "✏️ Редактировать конкретный товар" - "{EDIT_ITEM_CB}{item.id}" / "🔄 Изменить" - EDIT_ITEM_CB
EDIT_FIELD_CB = "edit_field:"

def build_edit_item_keyboard(item_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📝 Название", callback_data=f"{EDIT_FIELD_CB}title")],
            [InlineKeyboardButton(text="📋 Описание", callback_data=f"{EDIT_FIELD_CB}description")],
            [InlineKeyboardButton(text="💰 Цена", callback_data=f"{EDIT_FIELD_CB}price")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data=f"{SHOW_ITEM_CB}{item_id}")],
        ]
    )