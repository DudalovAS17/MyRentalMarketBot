import logging
from dataclasses import dataclass
from typing import Iterable, Optional

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter
from aiogram.types import InlineKeyboardMarkup

logger = logging.getLogger(__name__)

@dataclass(frozen=True, slots=True)
class NotificationResult:
    """Результат попытки отправить уведомление в Telegram."""

    chat_id: int | str # кому отправили
    success: bool # кому не отправили
    error: Optional[str] = None # почему не отправили


class NotificationService:
    """Сервис отправки Telegram-уведомлений клиентам и сотрудникам."""

    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    # ─────────────────────────────────────── Send helpers ────────────────────────────────────────────────────────────
    @staticmethod
    def _normalize_text(text: str) -> str:
        normalized = text.strip()
        if not normalized:
            raise ValueError("Текст уведомления не может быть пустым")
        return normalized

    async def _send_message(
            self,
            *,
            chat_id: int | str,
            text: str,
            reply_markup: Optional[InlineKeyboardMarkup] = None,
            parse_mode: str = "HTML",
    ) -> NotificationResult:
        """Отправить одно сообщение и вернуть результат без проб_роса Telegram-ошибок."""
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

        except TelegramForbiddenError as exc:
            logger.warning("Нельзя отправить уведомление chat_id=%s: %s", chat_id, exc)
            return NotificationResult(chat_id=chat_id, success=False, error=str(exc))

        except TelegramBadRequest as exc:
            logger.warning("Некорректное уведомление для chat_id=%s: %s", chat_id, exc)
            return NotificationResult(chat_id=chat_id, success=False, error=str(exc))

        except TelegramAPIError as exc:
            logger.error("Telegram API error при отправке chat_id=%s: %s", chat_id, exc, exc_info=True)
            return NotificationResult(chat_id=chat_id, success=False, error=str(exc))

        except Exception as exc:
            logger.error("Неожиданная ошибка при отправке уведомления chat_id=%s: %s", chat_id, exc, exc_info=True)
            return NotificationResult(chat_id=chat_id, success=False, error=str(exc))

        logger.info("Уведомление отправлено: chat_id=%s", chat_id)
        return NotificationResult(chat_id=chat_id, success=True)

    # ───────────────────────────────────────── Public API ────────────────────────────────────────────────────────────
    async def notify_user(
            self,
            user_id: int | str,
            text: str,
            reply_markup: Optional[InlineKeyboardMarkup] = None
    ) -> bool:
        """Отправить уведомление одному пользователю. Возвращает True, если Telegram принял сообщение."""
        normalized_text = self._normalize_text(text)
        result = await self._send_message(chat_id=user_id, text=normalized_text, reply_markup=reply_markup)
        return result.success

    async def notify_users(
            self,
            user_ids: Iterable[int | str],
            text: str,
            reply_markup: Optional[InlineKeyboardMarkup] = None
    ) -> list[NotificationResult]:
        """Отправить одинаковое уведомление нескольким пользователям."""
        results: list[NotificationResult] = []

        normalized_text = self._normalize_text(text)
        for user_id in user_ids:
            result = await self._send_message(chat_id=user_id, text=normalized_text, reply_markup=reply_markup)
            results.append(result)

        sent_count = sum(1 for result in results if result.success)
        logger.info("Массовое уведомление завершено: sent=%s failed=%s", sent_count, len(results) - sent_count)
        return results