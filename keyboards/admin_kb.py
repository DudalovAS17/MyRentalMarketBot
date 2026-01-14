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
