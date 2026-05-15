from services.notif_service import NotificationService

from schemas.item import ItemOut
from schemas.user import UserOut
from keyboards.rental_kb import get_open_rental_keyboard
from utils.notification import format_new_rental_request


async def notify_item_owner_about_rent_request(
        notification_service: NotificationService,
        owner_tg_id: int | None,
        item: ItemOut,
        user: UserOut,
        rental_id: int
) -> None:
    """Отправка уведомления владельцу о новом запросе аренды"""
    if owner_tg_id is None:
        return

    notify_text = format_new_rental_request(
        item_title=item.title,
        renter_username=user.username,
    )

    await notification_service.notify_user(
        owner_tg_id,
        notify_text,
        reply_markup=get_open_rental_keyboard(rental_id),
    )