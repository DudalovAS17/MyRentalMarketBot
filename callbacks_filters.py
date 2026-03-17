from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery

from config import settings


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