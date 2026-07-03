from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton

from utils.callbacks import PROFILE_EDIT_NAME, PROFILE_EDIT_EMAIL, PROFILE_BACK, PROFILE_BACK_TO_SETTINGS # PROFILE_EDIT_PHONE


# ────────────────────────────────────────────────── profile ───────────────────────────────────────────────────────────
def build_back_to_profile_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура возврата в профиль."""
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад в профиль", callback_data=PROFILE_BACK)]]
    )

# ────────────────────────────────────────────────── edit profile ──────────────────────────────────────────────────────
def build_edit_profile_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Изменить имя", callback_data=PROFILE_EDIT_NAME)],
            [InlineKeyboardButton(text="📧 Изменить Email", callback_data=PROFILE_EDIT_EMAIL)],
            # [InlineKeyboardButton(text="📱 Изменить телефон", callback_data=PROFILE_EDIT_PHONE)],
            [InlineKeyboardButton(text="« Назад", callback_data=PROFILE_BACK_TO_SETTINGS)],
        ]
    )

# ────────────────────────────────────────────────── phone ─────────────────────────────────────────────────────────────
def build_change_phone_keyboard() -> ReplyKeyboardMarkup:
    """Собрать клавиатуру отправки нового номера телефона."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Поделиться новым контактом", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

def build_open_profile_keyboard() -> InlineKeyboardMarkup:
    """Собрать клавиатуру возврата в профиль."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Открыть профиль", callback_data=PROFILE_BACK)]
        ]
    )

# ───────────────────────────────────────────────── privacy ────────────────────────────────────────────────────────────
def build_privacy_settings_keyboard() -> InlineKeyboardMarkup:
    """Собрать клавиатуру настроек конфиденциальности."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📄 Политика конфиденциальности",
                    callback_data="show_privacy_policy",
                )
            ],
            # [InlineKeyboardButton(
            #    text="Видимость профиля",
            #    callback_data="privacy_visibility"
            # )],
            [
                InlineKeyboardButton(
                    text="🔙 Назад в настройки",
                    callback_data="back_to_settings",
                )
            ],
        ],
    )

def build_privacy_policy_keyboard() -> InlineKeyboardMarkup:
    """Собрать клавиатуру политики конфиденциальности."""
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(
                text="🔙 Назад в настройки",
                callback_data="back_to_settings",
                )
            ]],
    )

# ───────────────────────────────────────────────── settings ───────────────────────────────────────────────────────────
def build_settings_keyboard() -> InlineKeyboardMarkup:
    """Собрать клавиатуру главного экрана настроек."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="🔔 Уведомления",
                callback_data="settings_notifications",
            )],
            [InlineKeyboardButton(
                text="✏️ Редактировать профиль",
                callback_data="settings_edit_profile",
            )],
            [InlineKeyboardButton(
                text="🔒 Конфиденциальность",
                callback_data="settings_privacy",
            )],
            # Меняем кнопку на возврат в профиль, так как это основной экран настроек
            [InlineKeyboardButton(
                text="🔙 Назад в профиль",
                callback_data=PROFILE_BACK,
            )],
        ],
    )

def build_notification_settings_keyboard(notifications_enabled: bool) -> InlineKeyboardMarkup:
    """Собрать клавиатуру настроек уведомлений."""
    if notifications_enabled:
        btn_text = "🔕 Выключить уведомления"
        btn_callback = "toggle_notifications:off"
    else:
        btn_text = "🔔 Включить уведомления"
        btn_callback = "toggle_notifications:on"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=btn_text,
                callback_data=btn_callback,
            )],
            [InlineKeyboardButton(
                text="« Назад",
                callback_data=PROFILE_BACK_TO_SETTINGS,
            )],
        ],
    )