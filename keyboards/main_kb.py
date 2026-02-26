from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from schemas.user import UserOut


def get_main_menu_keyboard(user: UserOut | None = None) -> ReplyKeyboardMarkup:
    """Создает клавиатуру главного меню с учетом информации о пользователе
        user_data (dict, optional): Данные пользователя для персонализации меню"""
    keyboard = [
        [KeyboardButton(text="🔍 Арендовать"), KeyboardButton(text="📦 Сдать в аренду")],
        [KeyboardButton(text="🔎 Поиск")],
        [KeyboardButton(text="📋 Мои сделки"), KeyboardButton(text="📞 Поддержка")],
        [KeyboardButton(text="👤 Профиль"), KeyboardButton(text="❓ Помощь")],
    ]

    # Если пользователь - администратор, добавляем кнопку админ-панели
    #if user and user.is_admin:
    #    keyboard.append([KeyboardButton(text="⚙️ Админ-панель")])

    # Если у пользователя есть непрочитанные уведомления
    if user and getattr(user, "unread_notifications", 0) > 0:
        unread_count = getattr(user, "unread_notifications", 0)
        keyboard[2][0] = KeyboardButton(text=f"👤 Профиль ({unread_count})")

    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def get_back_inline_keyboard(step_callback: str = None) -> InlineKeyboardMarkup:
    """ Создает inline-клавиатуру с кнопками возврата:
    - Назад (на предыдущий шаг) - step_callback (callback (str): данные, которые вернутся в callback при нажатии)
    - Отмена (в меню)"""

    if step_callback:
        buttons = [
            [
                InlineKeyboardButton(text="⬅️ Назад", callback_data=step_callback),
                InlineKeyboardButton(text="❌ Отмена", callback_data="back_to_menu")
            ]
        ]
    else:
        # Только кнопка отмены
        buttons = [
            [InlineKeyboardButton(text="❌ Отмена", callback_data="back_to_menu")]
        ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)




