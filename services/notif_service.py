import logging
from dataclasses import dataclass
from typing import Iterable, Optional

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter
from aiogram.types import InlineKeyboardMarkup

from schemas.rental import RentalAdminDetailsOut, RentalDetailsOut
from schemas.support import SupportTicketOut
from schemas.user import UserOut
from handlers.notification import (
    format_client_cancelled_rental,
    format_new_rental_request,
    format_new_support_ticket,
    format_support_closed,
    format_support_reply,
    format_support_user_reply,
    format_user_rental_created,
    format_user_rental_status_changed,
    format_user_support_created,
)
from handlers.support.helpers_support import build_support_continue_keyboard

logger = logging.getLogger(__name__)

@dataclass(frozen=True, slots=True)
class NotificationResult:
    """Результат попытки отправить уведомление в Telegram."""

    chat_id: int | str # кому отправили
    success: bool # кому не отправили
    error: Optional[str] = None # почему не отправили


class NotificationService:
    """Сервис безопасной отправки Telegram-уведомлений клиентам и сотрудникам."""

    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    # ─────────────────────────────────────── Send helpers ────────────────────────────────────────────────────────────
    @staticmethod
    def normalize_text(text: str) -> str:
        """Проверить и подготовить текст уведомления к отправке."""
        normalized = text.strip()
        if not normalized:
            raise ValueError("Текст уведомления не может быть пустым")
        return normalized

    async def send_message(
            self,
            *,
            chat_id: int | str,
            text: str,
            reply_markup: Optional[InlineKeyboardMarkup] = None,
            parse_mode: str = "HTML",
    ) -> NotificationResult:
        """Отправить одно сообщение и вернуть результат без проб_роса Telegram-ошибок в middleware."""
        try:
            await self.bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
            )

        except TelegramRetryAfter as exc:
            logger.warning("Telegram rate limit для chat_id=%s: %s", chat_id, exc)
            return NotificationResult(chat_id=chat_id, success=False, error=str(exc))

        except (TelegramBadRequest, TelegramForbiddenError) as exc:
            logger.warning("Не удалось отправить уведомление chat_id=%s: %s", chat_id, exc)
            return NotificationResult(chat_id=chat_id, success=False, error=str(exc))

        except TelegramAPIError as exc:
            logger.exception("Telegram API error при отправке chat_id=%s: %s", chat_id, exc)
            return NotificationResult(chat_id=chat_id, success=False, error=str(exc))

        logger.info("Уведомление отправлено: chat_id=%s", chat_id)
        return NotificationResult(chat_id=chat_id, success=True)

    # ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    async def send_to_user(self, telegram_id: int | str, text: str, *, reply_markup: Optional[InlineKeyboardMarkup] = None) -> bool:
        """Отправить сообщение одному Tg-пользователю по его telegram_id. Возвращает True, если Telegram принял сообщение."""
        result = await self.send_message(chat_id=telegram_id, text=self.normalize_text(text), reply_markup=reply_markup)
        return result.success

    async def notify_user(self, user_id: int | str, text: str, reply_markup: Optional[InlineKeyboardMarkup] = None) -> bool:
        """Backward-compatible alias для отправки уведомления одному пользователю."""
        return await self.send_to_user(user_id, text, reply_markup=reply_markup)

    async def notify_users(self, user_ids: Iterable[int | str], text: str, reply_markup: Optional[InlineKeyboardMarkup] = None) -> list[NotificationResult]:
        """Backward-compatible helper для массовой отправки с подробными результатами."""
        normalized_text = self.normalize_text(text)
        results = []
        for user_id in user_ids:
            results.append(await self.send_message(chat_id=user_id, text=normalized_text, reply_markup=reply_markup))
        return results

    async def send_to_admins(self, admin_ids: Iterable[int | str], text: str, *, reply_markup: Optional[InlineKeyboardMarkup] = None) -> dict[int | str, bool]:
        """Отправить одинаковое уведомление всем администраторам из ADMIN_IDS."""
        normalized_text = self.normalize_text(text)
        results: dict[int | str, bool] = {}
        for admin_id in admin_ids:
            result = await self.send_message(chat_id=admin_id, text=normalized_text, reply_markup=reply_markup)
            results[admin_id] = result.success

        logger.info("Уведомления админам завершены: %s", results)
        return results


    # ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    async def notify_admins_new_rental(self, admin_ids: Iterable[int], rental_details: RentalDetailsOut | RentalAdminDetailsOut, *, reply_markup=None) -> dict[int | str, bool]:
        """Уведомить администраторов о новой заявке на аренду."""
        return await self.send_to_admins(admin_ids, format_new_rental_request(rental_details), reply_markup=reply_markup)

    async def notify_user_rental_created(self, user_telegram_id: int, rental_details: RentalDetailsOut | RentalAdminDetailsOut) -> bool:
        """Уведомить клиента, что его заявка на аренду создана."""
        return await self.send_to_user(user_telegram_id, format_user_rental_created(rental_details))

    async def notify_user_rental_status_changed(self, user_telegram_id: int, rental_details: RentalDetailsOut | RentalAdminDetailsOut) -> bool: # , old_status=None
        """Уведомить клиента о новом статусе заявки на аренду."""
        return await self.send_to_user(user_telegram_id, format_user_rental_status_changed(rental_details)) # , old_status

    async def notify_user_rental_cancelled(self, user_telegram_id: int, rental_details: RentalDetailsOut | RentalAdminDetailsOut) -> bool:
        """Уведомить клиента об успешной отмене заявки с его стороны."""
        return await self.notify_user_rental_status_changed(user_telegram_id, rental_details)

    async def notify_admins_client_cancelled_rental(self, admin_ids: Iterable[int], rental_details: RentalDetailsOut | RentalAdminDetailsOut) -> dict[int | str, bool]:
        """Уведомить администраторов, что клиент отменил заявку."""
        return await self.send_to_admins(admin_ids, format_client_cancelled_rental(rental_details))

    async def notify_admins_new_support_ticket(self, admin_ids: Iterable[int], ticket: SupportTicketOut, user: UserOut, *, reply_markup=None) -> dict[int | str, bool]:
        """Уведомить администраторов о новом обращении в поддержку."""
        return await self.send_to_admins(admin_ids, format_new_support_ticket(ticket, user), reply_markup=reply_markup)

    async def notify_user_support_ticket_created(self, user_telegram_id: int) -> bool: # , ticket: SupportTicketOut | None = None
        """Уведомить клиента, что обращение в поддержку создано."""
        return await self.send_to_user(user_telegram_id, format_user_support_created()) # ticket

    async def notify_admins_support_user_reply(self, admin_ids: Iterable[int], ticket: SupportTicketOut, user: UserOut, reply_text: str, *, reply_markup=None) -> dict[int | str, bool]:
        """Уведомить администраторов о новом сообщении клиента в открытом тикете."""
        return await self.send_to_admins(admin_ids, format_support_user_reply(ticket, user, reply_text), reply_markup=reply_markup)

    async def notify_user_support_reply(self, user_telegram_id: int, ticket: SupportTicketOut, reply_text: str) -> bool:
        """Отправить клиенту ответ сотрудника по обращению в поддержку."""
        return await self.send_to_user(
            user_telegram_id,
            format_support_reply(ticket, reply_text),
            reply_markup=build_support_continue_keyboard(ticket.id)
        )

    async def notify_user_support_ticket_closed(self, user_telegram_id: int, ticket: SupportTicketOut) -> bool:
        """Уведомить клиента, что его обращение в поддержку закрыто."""
        return await self.send_to_user(user_telegram_id, format_support_closed(ticket))