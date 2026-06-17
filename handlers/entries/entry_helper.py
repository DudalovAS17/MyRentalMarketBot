from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

from keyboards.category_kb import build_category_keyboard
from status.rental_status import OPEN_STATUSES
from utils.callbacks import CAT_CB_PREFIX,  SEARCH_CITY_CB, SEARCH_FILTERS_CB, BACK_TO_MENU_CB, RENTAL_DETAILS_CB

# ──────────────────────────────────────────── base ────────────────────────────────────────────────────────────────────
def build_main_menu_text(user) -> str:
    welcome_message = (
        "🏠 <b>Главное меню</b>\n\n "
        f"Здравствуйте, <b>{user.full_name or user.first_name or user.username or 'пользователь'}</b>!\n\n"
        "Выберите действие:"
    )
    return welcome_message

# ───────────────────────────────────────────── category ───────────────────────────────────────────────────────────────
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

def build_registration_welcome_text() -> str:
    return (
        "👋 Приветствуем в <b>Аренда.рф</b>!\n\n"
        "Здесь вы можете арендовать вещи по всей России.\n\n"
        "Для безопасности, пожалуйста, подтвердите номер телефона:"
        # тут надо норм текст при для 1-й регистрации
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