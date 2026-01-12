from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_profile_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура профиля пользователя"""
    builder = InlineKeyboardBuilder()

    builder.button(text="📦 Мои объявления", callback_data="my_items")
    builder.button(text="📋 Мои сделки", callback_data="my_rentals")
    builder.button(text="🏆 Достижения", callback_data="achievements")
    builder.button(text ="📊 Статистика", callback_data="profile_stats")
    builder.button(text="📱 Изменить номер", callback_data="profile_change_phone")
    builder.button(text="🔔 Уведомления", callback_data="profile_notifications")
    builder.button(text = "✏️ Редактировать профиль", callback_data="profile_settings") # "⚙️ Настройки" # "edit_profile"
    builder.button(text = "📞 Поддержка", callback_data="profile_help")
    builder.button(text = "⬅️ В главное меню", callback_data="back_to_main_menu") # ?

    # Если у пользователя есть непрочитанные уведомления
    # if user_data and user_data.get('unread_notifications', 0) > 0:
    # Заменяем кнопку уведомлений на кнопку с счетчиком
    #    unread_count = user_data.get('unread_notifications', 0)
    #    keyboard[2][1] = KeyboardButton(f"🔔 Уведомления ({unread_count})")

    # раскладываем по 2 кнопки в ряд
    builder.adjust(2)

    return builder.as_markup()

def profile_settings_back_keyboard() -> InlineKeyboardMarkup:
    """Кнопка 'Назад в настройки'."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="« Назад", callback_data="back_to_profile_settings")]
        ]
    )

def get_review_rating_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⭐", callback_data="review_rating:1"),
                InlineKeyboardButton(text="⭐⭐", callback_data="review_rating:2"),
                InlineKeyboardButton(text="⭐⭐⭐", callback_data="review_rating:3"),
                InlineKeyboardButton(text="⭐⭐⭐⭐", callback_data="review_rating:4"),
                InlineKeyboardButton(text="⭐⭐⭐⭐⭐", callback_data="review_rating:5"),
            ],
            [
                InlineKeyboardButton(text="❌ Отмена", callback_data="review_cancel"),
            ],
        ]
    )

