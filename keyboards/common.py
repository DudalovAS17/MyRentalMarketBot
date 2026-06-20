from typing import Sequence
from datetime import date, timedelta
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

#from handlers.auth.helpers_auth.keyboards import BACK_TO_SETTINGS
from schemas.category import CategoryOut
from status.rental_status import OPEN_STATUSES
from utils.callbacks import (CAT_CB_PREFIX,  SEARCH_CITY_CB, SEARCH_FILTERS_CB, BACK_TO_MENU_CB, RENTAL_DETAILS_CB,
                             CANCEL_RENT_FLOW_CB, START_DATE_CB, CONFIRM_RENT_CB)

BACK_TO_SETTINGS = "back_to_profile_settings"

# ──────────────────────────────────────────── base ────────────────────────────────────────────────────────────────────
def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура главного меню клиента (с учетом информации о нем)"""
    keyboard = [
        [KeyboardButton(text="🔍 Арендовать"), KeyboardButton(text="🔎 Поиск")],
        [KeyboardButton(text="📋 Мои сделки"), KeyboardButton(text="👤 Профиль")],
        [KeyboardButton(text="📞 Поддержка"), KeyboardButton(text="❓ Помощь")],
    ]

    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True, input_field_placeholder="Выберите действие")


# ───────────────────────────────────────────── category ───────────────────────────────────────────────────────────────
"""
build_category_keyboard() универсальный 👌, подходит для:
    - категорий (нужны “🏙️ город / ⚙️ фильтры / 🔙 меню”)
    - подкатегорий (нужны “📋 все в категории / 🔙 назад”)
    - админских списков (нужны “➕ создать / ❌ отмена”)

categories: Sequence[CategoryOut]
    - Ты передаёшь list[CategoryOut] → а list является Sequence, значит всё ок.
"""
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
            [InlineKeyboardButton(text="🏙️ Поиск по городу", callback_data=SEARCH_CITY_CB)],
            [InlineKeyboardButton(text="⚙️ Фильтры", callback_data=SEARCH_FILTERS_CB)],
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


def build_my_rentals_keyboard(rentals, *, current_user_id: int, limit: int = 30) -> InlineKeyboardMarkup:
    """Собрать клавиатуру списка сделок пользователя"""
    rows: list[list[InlineKeyboardButton]] = []

    for rental in sort_rentals_for_list(rentals)[:limit]: # MVP-ограничение списка
        button_text = build_rental_list_button_text(rental, current_user_id=current_user_id)
        rows.append([InlineKeyboardButton(text=button_text[:64], callback_data=f"{RENTAL_DETAILS_CB}{rental.id}")])

    rows.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data=BACK_TO_MENU_CB)])

    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_open_rental_keyboard(rental_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Открыть сделку", callback_data=f"rental_details:{rental_id}")],
        ] # "🔍 Посмотреть запрос"
    )

def build_rent_end_date_keyboard(start_date: date, min_days: int, max_days: int, options: int = 6) -> InlineKeyboardMarkup:
    """
    Клавиатура выбора даты окончания аренды.
    Показываем 'options' вариантов начиная с min_days, но не выходя за max_days.
    """

    min_days = max(min_days, 1)
    max_days = max(max_days, min_days)

    # Покажем до 6 вариантов: min_days ... min_days + options, но не больше max_days
    option_days = [d for d in range(min_days, min_days + options) if d <= max_days] or [min_days]

    rows: list[list[InlineKeyboardButton]] = [
        [InlineKeyboardButton(text="📅 Выберите дату окончания аренды:", callback_data="ignore")]
    ]

    for days in option_days:
        end_date = start_date + timedelta(days=days)
        end_str = end_date.strftime("%d.%m.%Y")
        rows.append(
            [InlineKeyboardButton(text=f"{end_str}  ({days} дн.)", callback_data=f"end_date:{end_str}:{days}")]
        )

    rows.append([InlineKeyboardButton(text="❌ Отмена", callback_data=CANCEL_RENT_FLOW_CB)])
    #rows.append([InlineKeyboardButton(text="🔙 Назад к выбору даты начала", callback_data=f"rent_item:{item_id}")])

    return InlineKeyboardMarkup(inline_keyboard=rows)

def build_rent_confirmation_keyboard(start_date: str) -> InlineKeyboardMarkup:
    """Клавиатура финального шага подтверждения аренды."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Отправить запрос владельцу", callback_data=CONFIRM_RENT_CB)],
            [InlineKeyboardButton(text="🔙 Изменить дату окончания", callback_data=f"{START_DATE_CB}{start_date}")],
            [InlineKeyboardButton(text="❌ Отменить аренду", callback_data=CANCEL_RENT_FLOW_CB)], # или f"{ITEM_DETAILS}{item_id}"???
        ]
    )


# ───────────────────────────────────────────────── user ───────────────────────────────────────────────────────────────
def get_profile_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура профиля пользователя"""
    builder = InlineKeyboardBuilder()

    builder.button(text="📦 Мои объявления", callback_data="my_items")
    builder.button(text="📋 Мои сделки", callback_data="my_rentals")
    builder.button(text="🏆 Достижения", callback_data="achievements")
    builder.button(text ="📊 Статистика", callback_data="profile_stats")
    builder.button(text="📱 Изменить номер", callback_data="profile_change_phone")
    builder.button(text="🔔 Уведомления", callback_data="profile_notifications") # "settings_notifications"
    builder.button(text = "✏️ Редактировать профиль", callback_data="profile_settings") # "⚙️ Настройки" # "edit_profile"
    builder.button(text = "📞 Поддержка", callback_data="profile_help") # "support:start"
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
            [InlineKeyboardButton(text="« Назад", callback_data=BACK_TO_SETTINGS)]
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
def build_search_keyboard(items, page: int, has_next: bool) -> InlineKeyboardMarkup:
    keyboard: list[list[InlineKeyboardButton]] = []

    for item in items:
        keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"🔎 Открыть #{item.id}",
                    callback_data=f"show_item_details:{item.id}",
                )
            ]
        )

    has_prev = page > 1
    nav_row: list[InlineKeyboardButton] = []
    if has_prev:
        nav_row.append(InlineKeyboardButton(text="⬅️ Пред", callback_data=f"search:page:{page - 1}"))
    if has_next:
        nav_row.append(InlineKeyboardButton(text="➡️ След", callback_data=f"search:page:{page + 1}"))
    if nav_row:
        keyboard.append(nav_row)

    keyboard.append([InlineKeyboardButton(text="✏️ Новый запрос", callback_data="search:new_query")])
    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="search:back")]) # "back_to_main_menu"

    return InlineKeyboardMarkup(inline_keyboard=keyboard)




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

def build_rental_list_button_text(rental, current_user_id: int) -> str:
    """Собрать текст кнопки сделки для списка"""

    role_label = "Ваша заявка" if rental.user_id == current_user_id else "Заявка"
    status_label = rental.status.value #STATUS_LABELS.get(rental.status, rental.status.value)
    item_label = f"Товар #{rental.item_id}"

    return f"# Заявка {rental.id} • {role_label} • {item_label} • 🔖 Статус: {status_label}"





# ───────────────────────────────────────────── no used ────────────────────────────────────────────────────────────────
def get_back_inline_keyboard(step_callback: str = None) -> InlineKeyboardMarkup:
    """Клавиатуру возврата

    - Назад (на предыдущий шаг)
    - Отмена (в меню) """

    if step_callback:
        buttons = [[InlineKeyboardButton(text="⬅️ Назад", callback_data=step_callback),
                    InlineKeyboardButton(text="❌ Отмена", callback_data="back_to_main_menu")]] # "back_to_menu"
    else:
        buttons = [[InlineKeyboardButton(text="❌ Отмена", callback_data="back_to_main_menu")]] # "back_to_menu"

    return InlineKeyboardMarkup(inline_keyboard=buttons)