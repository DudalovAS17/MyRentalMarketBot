from __future__ import annotations

import logging
from datetime import datetime

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from config import ADMIN_IDS
from keyboards.admin_kb import get_admin_support_ticket_notification_keyboard
from services.support_service import SupportService
from states.support_ticket import SupportStates
from utils.functions import send_or_edit

logger = logging.getLogger(__name__)

support_router = Router()


def _format_datetime(dt: datetime | None) -> str:
    if not dt:
        return "—"
    return dt.strftime("%d.%m.%Y %H:%M")


def _render_admin_ticket_message(ticket, user) -> str:
    username = f"@{user.username}" if user and user.username else "—"
    created_at = _format_datetime(getattr(ticket, "created_at", None))
    return (
        "🆘 <b>Новый тикет поддержки</b>\n\n"
        f"🎫 <b>Тикет:</b> #{ticket.id}\n"
        f"👤 <b>Пользователь:</b> {user.display_name if user else '—'}\n"
        f"🆔 <b>Telegram ID:</b> <code>{user.telegram_id if user else '—'}</code>\n"
        f"💬 <b>Username:</b> {username}\n"
        f"📅 <b>Создан:</b> {created_at}\n"
        f"📝 <b>Текст:</b>\n{ticket.text}"
    )


@support_router.message(Command("support"))
@support_router.callback_query(F.data.in_(["support:start", "profile_help"]))
async def start_support(event: Message | CallbackQuery, state: FSMContext, support_service: SupportService, user):
    if isinstance(event, CallbackQuery):
        await event.answer()

    open_ticket = await support_service.get_open_ticket_by_user(user.id)
    if open_ticket:
        return await send_or_edit(
            event,
            f"⚠️ У вас уже есть открытый тикет #{open_ticket.id}. "
            "Дождитесь ответа поддержки.",
            markup=None,
        )

    await state.set_state(SupportStates.waiting_text)
    return await send_or_edit(
        event,
        "🆘 <b>Поддержка</b>\n\n"
        "Опишите вашу проблему или вопрос одним сообщением. Мы постараемся помочь как можно скорее.",
        markup=None,
    )


@support_router.message(SupportStates.waiting_text, F.text)
async def receive_support_text(
    message: Message,
    state: FSMContext,
    support_service: SupportService,
    user,
):
    text = (message.text or "").strip()
    if not text:
        return await send_or_edit(message, "Пожалуйста, отправьте текст обращения.")

    open_ticket = await support_service.get_open_ticket_by_user(user.id)
    if open_ticket:
        await state.clear()
        return await send_or_edit(
            message,
            f"⚠️ У вас уже есть открытый тикет #{open_ticket.id}. "
            "Дождитесь ответа поддержки."
        )

    ticket = await support_service.create_ticket(user_id=user.id, text=text)
    await state.clear()

    await send_or_edit(
        message,
        f"✅ Обращение принято! Номер тикета: #{ticket.id}. Мы свяжемся с вами как можно скорее."
    )

    if not ADMIN_IDS:
        logger.warning("ADMIN_IDS пустой — уведомления о тикете не отправлены.")
        return

    notification_text = _render_admin_ticket_message(ticket, user)
    markup = get_admin_support_ticket_notification_keyboard(ticket.id)

    for admin_id in ADMIN_IDS:
        try:
            await message.bot.send_message(
                chat_id=admin_id,
                text=notification_text,
                reply_markup=markup,
                parse_mode="HTML",
            )
        except Exception as exc:
            logger.error("Не удалось уведомить админа %s о тикете %s: %s", admin_id, ticket.id, exc)
