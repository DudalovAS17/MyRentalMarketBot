from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery

from config import settings
from status.user_status import AccountStatus

# Не используется. Данная логика реализуется через Middleware

class UserAccessFilter(BaseFilter):
    """
    нет пользователя → не пускаем;
    есть пользователь, но account_status != ACTIVE → не пускаем;
    есть пользователь и ACTIVE → пускаем.
    """
    async def __call__(self, event: Message | CallbackQuery, user) -> bool:
        if user is None:
            if isinstance(event, CallbackQuery):
                await event.answer("Сначала завершите регистрацию через /start.", show_alert=True)
            else:
                await event.answer("Сначала завершите регистрацию через /start.")
            return False

        if user.account_status != AccountStatus.ACTIVE:
            if isinstance(event, CallbackQuery):
                await event.answer("⛔ Доступ к этому разделу ограничен.", show_alert=True)
            else:
                await event.answer("⛔ Доступ к этому разделу ограничен.")
            return False

        return True


class AdminIdFilter(BaseFilter):
    async def __call__(self, event: Message | CallbackQuery) -> bool:
        user = event.from_user
        return bool(user and user.id in settings.admin_ids)

class PrivateChatFilter(BaseFilter):
    async def __call__(self, event: Message | CallbackQuery) -> bool:
        chat = event.message.chat if isinstance(event, CallbackQuery) else event.chat
        return chat.type == "private"

# UserExistsFilter
# NotBlockedFilter