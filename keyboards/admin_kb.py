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