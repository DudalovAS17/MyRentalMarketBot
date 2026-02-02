from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_admin_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📄 Модерация сделок", callback_data="admin:deals"),
                InlineKeyboardButton(text="📦 Модерация объявлений", callback_data="admin:items"),
            ],
            [
                InlineKeyboardButton(text="👥 Управление пользователями", callback_data="admin:users"),
                InlineKeyboardButton(text="⚠️ Жалобы/споры", callback_data="admin:disputes"),
            ],
            [
                InlineKeyboardButton(text="🆘 Поддержка", callback_data="admin:support"),
                InlineKeyboardButton(text="📚 Контент/FAQ", callback_data="admin:content"),
            ],
            [
                InlineKeyboardButton(text="🔙 Назад в меню", callback_data="admin:exit"),
            ], # 📊 Статистика, 📢 Рассылка сообщений, ⚙️ Настройки бота
        ]
    )

def get_back_to_admin_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад в админ-меню", callback_data="admin:menu")]
        ]
    )


# ============================================ ADMIN DEALS ================================================
def get_admin_deals_list_keyboard(rentals_rows: list[dict], page: int, has_next: bool) -> InlineKeyboardMarkup:
    kb = []

    for row in rentals_rows:
        r = row["rental"]
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


def get_admin_deal_details_keyboard(rental_id: int, status_value: str) -> InlineKeyboardMarkup:
    kb = []

    kb.append([InlineKeyboardButton(text="🔄 Обновить", callback_data=f"admin:deals:view:{rental_id}")])

    kb.append([InlineKeyboardButton(text="🚫 Отменить сделку", callback_data=f"admin:deals:cancel:{rental_id}")])

    # Кнопка “закрыть спор” только если статус disputed
    if status_value == "disputed":
        kb.append([InlineKeyboardButton(text="✅ Закрыть спор", callback_data=f"admin:deals:resolve:{rental_id}")])

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
# ==============================================================================================================

# ============================================ ADMIN SUPPORT =============================================
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

def get_admin_support_ticket_keyboard(ticket_id: int, status_value: str) -> InlineKeyboardMarkup:
    kb = []
    kb.append([InlineKeyboardButton(text="🔄 Обновить", callback_data=f"admin:support:view:{ticket_id}")])

    if status_value == "open":
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
# ==============================================================================================================


# ============================================ ADMIN ITEMS ================================================
def get_admin_items_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🟡 PENDING", callback_data="admin:items:filter:PENDING")],
            [InlineKeyboardButton(text="✅ ACTIVE", callback_data="admin:items:filter:ACTIVE")],
            [InlineKeyboardButton(text="🙈 HIDDEN", callback_data="admin:items:filter:HIDDEN")],
            [InlineKeyboardButton(text="🔙 Назад в админ-меню", callback_data="admin:menu")],
        ]
    )

def get_admin_items_list_keyboard(
        items: list,
        status: str,
        page: int,
        has_next: bool
) -> InlineKeyboardMarkup:
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


def get_admin_item_details_keyboard(item_id: int, status_value: str) -> InlineKeyboardMarkup:
    kb = []
    kb.append([InlineKeyboardButton(text="🔄 Обновить", callback_data=f"admin:items:view:{item_id}")])

    if status_value == "PENDING":
        kb.append([InlineKeyboardButton(text="✅ Сделать ACTIVE", callback_data=f"admin:items:approve:{item_id}")])
        kb.append([InlineKeyboardButton(text="❌ Reject", callback_data=f"admin:items:reject:{item_id}")])
    if status_value == "ACTIVE":
        kb.append([InlineKeyboardButton(text="🙈 Hide", callback_data=f"admin:items:hide:{item_id}")])
    if status_value == "HIDDEN":
        kb.append([InlineKeyboardButton(text="👁️ Unhide", callback_data=f"admin:items:unhide:{item_id}")])

    kb.append([InlineKeyboardButton(text="🔙 К списку", callback_data="admin:items")])

    return InlineKeyboardMarkup(inline_keyboard=kb)
# ==============================================================================================================