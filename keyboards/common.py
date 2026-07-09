from typing import Sequence
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

from schemas.category import CategoryOut
from status.rental_status import OPEN_STATUSES, STATUS_LABELS
from utils.callbacks import CAT_CB_PREFIX, BACK_TO_MENU_CB, RENTAL_DETAILS_CB, PROFILE_BACK_TO_SETTINGS, MY_RENTALS_CB
# SEARCH_CITY_CB, SEARCH_FILTERS_CB, CANCEL_RENT_FLOW_CB, CONFIRM_RENT_CB, RENT_BACK_CB, RENT_CHANGE_CB,

# ──────────────────────────────────────────── base ────────────────────────────────────────────────────────────────────
def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура главного меню клиента (с учетом информации о нем)"""
    keyboard = [
        [KeyboardButton(text="🛠 Каталог товаров"), KeyboardButton(text="🔎 Поиск")],
        [KeyboardButton(text="📋 Мои аренды"), KeyboardButton(text="👤 Профиль")],
        [KeyboardButton(text="📞 Поддержка"), KeyboardButton(text="❓ Помощь")], # ℹ️ Условия аренды
    ]

    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True, input_field_placeholder="Выберите действие")


# ───────────────────────────────────────────── category ───────────────────────────────────────────────────────────────
def build_category_keyboard(
    categories: Sequence[CategoryOut],
    prefix: str,
    *,
    extra_buttons: list[list[InlineKeyboardButton]] | None = None
) -> InlineKeyboardMarkup:
    """Универсальный генератор клавиатур для категорий / подкатегорий.

        prefix callback_data: 'cat:' / 'create_cat:'
        buttons_per_row: количество кнопок в строке
        extra_buttons: дополнительные кнопки (например 'Назад' или 'Отмена')
    """

    # строим клавиатуру (2 кнопки в ряд)
    rows: list[list[InlineKeyboardButton]] = [] # keyboard_rows
    row: list[InlineKeyboardButton] = []

    for i, cat in enumerate(categories, start=1):
        btn_text = f"{(cat.emoji or '').strip()} {cat.name}".strip() # "🏕️ Туризм и спорт"
        btn_cb = f"{prefix}{cat.id}" # CAT_CB_PREFIX
        row.append(InlineKeyboardButton(text=btn_text, callback_data=btn_cb))

        if i % 2 == 0: # i % buttons_per_row
            rows.append(row)
            row = []

    if row:
        rows.append(row)

    if extra_buttons:
        rows.extend(extra_buttons)

    return InlineKeyboardMarkup(inline_keyboard=rows)

def build_categories_screen_keyboard(categories) -> InlineKeyboardMarkup:
    return build_category_keyboard(
        categories,
        prefix=CAT_CB_PREFIX,
        extra_buttons=[
            #[InlineKeyboardButton(text="🏙️ Поиск по городу", callback_data=SEARCH_CITY_CB)],
            #[InlineKeyboardButton(text="⚙️ Фильтры", callback_data=SEARCH_FILTERS_CB)],
            [InlineKeyboardButton(text="🔙 Назад в меню", callback_data=BACK_TO_MENU_CB)]
        ]
    )


# ───────────────────────────────────────────── auth ───────────────────────────────────────────────────────────────────
def build_registration_contact_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Отправить номер телефона", request_contact=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


# ───────────────────────────────────────────── rentals ────────────────────────────────────────────────────────────────
def build_empty_my_rentals_keyboard() -> InlineKeyboardMarkup:
    """Собрать клавиатуру для пустого списка заявок."""
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🏠 Главное меню", callback_data=BACK_TO_MENU_CB)]]
    )


def build_my_rentals_keyboard(rentals, *, limit: int = 30) -> InlineKeyboardMarkup:
    """Собрать клавиатуру списка сделок пользователя"""
    rows: list[list[InlineKeyboardButton]] = []

    sorted_rentals = sort_rentals_for_list(rentals)
    for user_rental_number, rental in enumerate(sorted_rentals[:limit], start=1): # MVP-ограничение списка
        button_text = build_rental_list_button_text(rental, user_rental_number=user_rental_number)
        rows.append([InlineKeyboardButton(text=button_text[:64], callback_data=f"{RENTAL_DETAILS_CB}{rental.id}")])
    rows.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data=BACK_TO_MENU_CB)])

    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_open_rental_keyboard(rental_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Открыть заявку", callback_data=f"rental_details:{rental_id}")],
        ] # "🔍 Посмотреть запрос"
    )

# def build_rent_confirmation_keyboard() -> InlineKeyboardMarkup: # start_date: str
#     """Клавиатура финального шага подтверждения аренды."""
#     return InlineKeyboardMarkup(
#         inline_keyboard=[
#             [InlineKeyboardButton(text="✅ Отправить заявку менеджеру", callback_data=CONFIRM_RENT_CB)],
#             [InlineKeyboardButton(text="✏️ Изменить", callback_data=RENT_CHANGE_CB)],
#             [InlineKeyboardButton(text="⬅️ Назад", callback_data=RENT_BACK_CB)],
#             [InlineKeyboardButton(text="❌ Отменить аренду", callback_data=CANCEL_RENT_FLOW_CB)], # или f"{ITEM_DETAILS}{item_id}"???
#         ]
#     )
# # [InlineKeyboardButton(text="🔙 Изменить дату окончания", callback_data=f"{START_DATE_CB}{start_date}")],

# ───────────────────────────────────────────────── user ───────────────────────────────────────────────────────────────
def get_profile_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура профиля пользователя"""
    builder = InlineKeyboardBuilder()

    builder.button(text="📋 Мои аренды", callback_data=MY_RENTALS_CB)
    builder.button(text="✏️ Контактные данные", callback_data="settings_edit_profile") # "profile_settings", "edit_profile"

    #builder.button(text="🏆 Достижения", callback_data="achievements")
    #builder.button(text ="📊 Статистика", callback_data="profile_stats")

    #builder.button(text="🕘 История обращений", callback_data=PROFILE_SUPPORT_HISTORY)
    builder.button(text="🔔 Уведомления", callback_data="profile_notifications")  # "settings_notifications"

    builder.button(text = "⬅️ В главное меню", callback_data=BACK_TO_MENU_CB)

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
            [InlineKeyboardButton(text="« Назад", callback_data=PROFILE_BACK_TO_SETTINGS)]
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


# ───────────────────────────────────────────────── search ─────────────────────────────────────────────────────────────


# ───────────────────────────────────────────── rentals-helpers ────────────────────────────────────────────────────────────────
def sort_rentals_for_list(rentals):
    """Отсортировать заявки для списка: открытые сверху, новые выше."""
    return sorted(
        rentals,
        key=lambda rental: ( # берёт каждый элемент из списка rentals
            0 if rental.status in OPEN_STATUSES else 1,
            -rental.id,
        )
    )

def build_rental_list_button_text(rental, *, user_rental_number: int) -> str:
    """Собрать текст кнопки заявки для списка."""
    status_label = STATUS_LABELS.get(rental.status, rental.status.value) # • {rental.item_id}
    return f"# Заявка {user_rental_number} • 🏷 Статус: {status_label}"

# ───────────────────────────────────────────── общая ────────────────────────────────────────────────────────────────
def cancel_keyboard() -> InlineKeyboardMarkup:
    """Единая inline-клавиатура для FSM: только ❌ Отмена → главное меню."""
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="❌ Отмена", callback_data=BACK_TO_MENU_CB)]]
    )

# ───────────────────────────────────────────── no used ────────────────────────────────────────────────────────────────
def get_back_inline_keyboard(step_callback: str = None) -> InlineKeyboardMarkup:
    """Клавиатуру возврата

    - Назад (на предыдущий шаг)
    - Отмена (в меню) """

    if step_callback:
        buttons = [[InlineKeyboardButton(text="⬅️ Назад", callback_data=step_callback),
                    InlineKeyboardButton(text="❌ Отмена", callback_data=BACK_TO_MENU_CB)]] # "back_to_menu"
    else:
        buttons = [[InlineKeyboardButton(text="❌ Отмена", callback_data=BACK_TO_MENU_CB)]] # "back_to_menu"

    return InlineKeyboardMarkup(inline_keyboard=buttons)

# build_rent_end_date_keyboard - Клавиатура выбора даты окончания аренды.