import logging
from typing import Iterable, Optional

from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup

logger = logging.getLogger(__name__)


class NotificationService:
    """Минимальный сервис отправки уведомлений через bot.send_message."""

    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    async def notify_user(
        self,
        user_id: int,
        text: str,
        reply_markup: Optional[InlineKeyboardMarkup] = None,
    ) -> None:
        try:
            await self.bot.send_message(
                chat_id=user_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode="HTML",
            )
        except Exception as exc:
            logger.error("Не удалось отправить уведомление пользователю %s: %s", user_id, exc, exc_info=True)

    async def notify_users(
        self,
        user_ids: Iterable[int],
        text: str,
        reply_markup: Optional[InlineKeyboardMarkup] = None,
    ) -> None:
        for user_id in user_ids:
            await self.notify_user(user_id, text, reply_markup=reply_markup)