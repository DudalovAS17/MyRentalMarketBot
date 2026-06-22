from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from status.rental_status import RentalStatus, STATUS_LABELS
from schemas.rental import RentalDetailsOut, RentalOut
from utils.callbacks import MY_RENTALS_CB, BACK_TO_MENU_CB, IGNORE_CB, CLIENT_CANCEL_RENTAL_CB, CLIENT_SUPPORT_RENTAL_CB
from utils.ui_defaults import ui_str, ui_money

# "✅ Подтвердить получение товара"
# "📦 Компания Передала товар"
# "❌ Отклонить аренду/заявку"
# text="⚠️ Открыть спор", callback_data=f"rental_action:dispute:{rental_id}"
# text="💬 Написать в поддержку", callback_data = f"support_chat:{rental_id}"
# text="⭐ Оставить отзыв", callback_data=f"review_start:{rental_id}"
# text="⭐ Посмотреть отзыв", callback_data=f"review_view:{rental_id}"

def _fmt_date(value) -> str:
    return value.strftime("%d.%m.%Y") if value else "—"

def _fmt_bool(value: bool | None) -> str:
    if value: # is True
        return "нужна."
    if value is False:
        return "не нужна."
    return "—"

def format_rental_status(status: RentalStatus) -> str:
    return status.value.replace("_", " ").replace("-", " ").capitalize()

def build_rental_details_ui(details: RentalDetailsOut) -> tuple[str, InlineKeyboardMarkup]:
    """Собрать текст и клавиатуру клиентского экрана деталей заявки."""

    #user = details.user
    rental = details.rental
    item = details.item

    status_text = STATUS_LABELS.get(rental.status, rental.status.value)
    item_title = ui_str(item.title, "Неизвестный товар")
    item_desc = ui_str(item.short_description or item.description, "—") # [:100]???

    item_price = ui_money(item.price, "0")
    total_price = ui_money(rental.total_price, "—")
    final_price = ui_money(rental.final_price, "—")

    client_name = ui_str(rental.client_name, "—")
    client_phone = ui_str(rental.client_phone, "—")

    text = (
        #f"🔎 <b>Заявка #{rental.id}</b>\n\n"
        f"📦 <b>Товар:</b> {item_title}\n"
        
        f"<b>Описание:</b> {item_desc}\n"
        f"💰 <b>Цена:</b> {item_price} ₽/день\n"
        #f"🔢 <b>Количество:</b> {rental.quantity}\n\n"
        
        f"<b>Период аренды:</b>\n"
        #f"📅 Начало: <b>{_fmt_date(rental.start_date):%d.%m.%Y}</b>\n"
        #f"📅 Конец: <b>{_fmt_date(rental.end_date):%d.%m.%Y}</b>\n"
        f"📝 Период: <b>{ui_str(rental.rental_period_text, '—')}</b>\n\n"
        
        f"<b>Доставка:</b> {_fmt_bool(rental.delivery_needed)}\n"
        f"📍 Адрес: {ui_str(rental.delivery_address, '—')}\n\n"
        
        f"<b>Контакты:</b>\n"
        f"👤 Имя: {client_name}\n"
        f"☎️ Телефон: {client_phone}\n"
        f"💬 Комментарий: {ui_str(rental.client_comment, '—')}\n\n"
        
        f"<b>Оплата:</b>\n"
        f"💵 Расчётная стоимость: <b>{total_price} ₽</b>\n"
        f"✅ Финальная стоимость: <b>{final_price} ₽</b>\n\n"
        
        f"<b>Статус заявки:</b> <b>{status_text}</b>"

        #f"\n<b>Подтверждения:</b>\n"
        # f"👑 Компания передала товар: {company_flag}\n"
        # f"👤 Вы получили товар: {client_flag}\n"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=build_client_actions(rental))

    return text, keyboard

def build_client_actions(rental: RentalOut) -> list[list[InlineKeyboardButton]]:
    """Собрать клиентские действия по заявке."""
    buttons: list[list[InlineKeyboardButton]] = []

    if rental.status in {
        RentalStatus.REQUESTED,
        RentalStatus.IN_PROGRESS,
        RentalStatus.CONFIRMED,
    }:
        buttons.append([
            InlineKeyboardButton(text="❌ Отменить заявку", callback_data=f"{CLIENT_CANCEL_RENTAL_CB}{rental.id}")
        ])

    # if can_cancel:
    #     buttons.append([
    #         InlineKeyboardButton(
    #             text="❌ Отменить заявку",
    #             callback_data=f"{CLIENT_CANCEL_RENTAL_CB}{rental.id}",
    #         )
    #     ])

    buttons.append([
        InlineKeyboardButton(text="💬 Написать в поддержку", callback_data=f"{CLIENT_SUPPORT_RENTAL_CB}{rental.id}")
    ])

    if rental.manager_comment:
        buttons.append([
            InlineKeyboardButton(text="ℹ️ Комментарий менеджера есть", callback_data=IGNORE_CB)
        ])

    buttons.append(
        [InlineKeyboardButton(text="🔙 Назад к списку заявок", callback_data=MY_RENTALS_CB)], # "rental_list"
    )
    buttons.append(
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data=BACK_TO_MENU_CB)]
    )

    return buttons