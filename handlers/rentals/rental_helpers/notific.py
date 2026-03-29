import logging

from services.user_service import UserService
from services.notif_service import NotificationService
from utils.errors import ServiceError
from keyboards.rental_kb import get_open_rental_keyboard
from utils.notification import format_new_rental_request

logger = logging.getLogger(__name__)

async def notify_item_owner_about_rent_request(user_service: UserService, notification_service: NotificationService,
                                               item, user, rental_id: int) -> None:
    """Уведомить владельца"""
    try:
        owner = await user_service.get_by_id(item.user_id)
    except ServiceError:
        owner = None

    owner_tg_id = getattr(owner, "telegram_id", None) if owner else None

    notify_text = format_new_rental_request(
        item_title=getattr(item, "title", "—"),
        renter_username=getattr(user, "username", None),
    )

    if owner_tg_id:
        # ✅ notify_user сам ловит TelegramBadRequest/Exception и логирует
        await notification_service.notify_user(
            owner_tg_id,
            notify_text,
            reply_markup=get_open_rental_keyboard(rental_id),
        )
    else:
        logger.warning(
            "Не удалось отправить уведомление владельцу user_id=%s: отсутствует telegram_id или владелец не найден",
            item.user_id, # owner_id
        )