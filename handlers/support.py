import logging
from datetime import datetime

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from services.support_service import SupportService, TicketAlreadyOpen
from states.support_ticket import SupportStates
from schemas.support import SupportTicketCreate, SupportTicketCreateInternal
from keyboards.admin_kb import get_admin_support_ticket_notification_keyboard
from utils.functions import send_or_edit

logger = logging.getLogger(__name__)

"""создание тикета + отправка админам"""
support_router = Router()

def _format_datetime(dt: datetime | None) -> str:
    if not dt:
        return "—"
    return dt.strftime("%d.%m.%Y %H:%M")

def _render_admin_ticket_message(ticket, user) -> str: # (ticket_id: int, user, text: str)
    tg_id = getattr(user, "telegram_id", None)
    username = getattr(user, "username", None)  # "—"
    #created = _format_datetime(getattr(ticket, "created", None))
    created = datetime.now().strftime("%d.%m.%Y %H:%M")
    return (
        f"🆘 🎫 <b>Новый тикет поддержки </b> #{ticket.id}\n\n"
        f"👤 <b>Пользователь:</b> @{username} (tg_id={tg_id}) \n" # full_name
        f"🆔 <b>Telegram ID:</b> <code>{user.telegram_id if user else '—'}</code>\n"
        f"📅 <b>Создан:</b> {created}\n"
        f"📝 <b>Текст:</b>\n{ticket.text}"
    )


# Вход: /support (если хочешь кнопку в меню — добавишь callback на "support:start")
@support_router.message(Command("support"))
async def support_start(message: Message, state: FSMContext, support_service: SupportService, user):
    """Старт поддержки через команду /support."""
    await _start_support_flow(message, state, support_service, user)

@support_router.callback_query(F.data == "support:start") # (F.data.in_(["support:start", "profile_help"]))
async def support_start_callback(callback: CallbackQuery, state: FSMContext, support_service: SupportService, user):
    """Старт поддержки через кнопку."""
    await _start_support_flow(callback, state, support_service, user)
    await callback.answer()

async def _start_support_flow(
    event: Message | CallbackQuery,
    state: FSMContext,
    support_service: SupportService,
    user,
) -> None:
    """Единый вход в поддержку:
        - не даём создать второй OPEN тикет
        - ставим FSM на ожидание текста
        - отвечаем через send_or_edit (универсально для Message/CallbackQuery)
    """
    open_ticket = await support_service.get_open_ticket_by_user(user.id)
    if open_ticket:
        await send_or_edit(
            event,
            f"⚠️ У вас уже есть открытое обращение (тикет #{open_ticket.id}).\n"
            f"Дождитесь ответа поддержки или создайте новое после закрытия.",
            markup=None,
        )
        return

    await state.set_state(SupportStates.waiting_text)
    await send_or_edit(
        event,
        "🆘 <b>Поддержка</b>\n\n"
        "Опишите вашу проблему или вопрос одним сообщением. Мы постараемся помочь как можно скорее.",
        markup=None,
    )


async def _notify_admins(bot, admin_ids: list[int], notification_text: str, ticket_id: int) -> None:
    if not admin_ids:
        logger.warning("ADMIN_IDS пустой — уведомления о тикете не отправлены.")
        return

    kb = get_admin_support_ticket_notification_keyboard(ticket_id)

    for admin_id in admin_ids:
        try:
            await bot.send_message(chat_id=admin_id, text=notification_text, reply_markup=kb, parse_mode="HTML")
        except Exception as exc:
            logger.error("Не удалось уведомить админа %s о тикете %s: %s", admin_id, ticket_id, exc)


@support_router.message(SupportStates.waiting_text, F.text) # F.text - чтобы только текст ловить (не смайлы/картинки)
async def receive_support_text(
    message: Message,
    state: FSMContext,
    support_service: SupportService,
    user,
    admin_ids: list[int],
):
    """Создание тикета и отправка уведомления админам."""
    text = (message.text or "").strip()
    if not text:
        return await send_or_edit(message, "Пожалуйста, отправьте текст обращения.")
        # await message.answer("❌ Текст не может быть пустым. Опишите проблему одним сообщением.")
        #  return

    try:
        internal = SupportTicketCreateInternal( # SupportTicketCreate- без user_id
                user_id=user.id,
                telegram_id=int(user.telegram_id),
                username=user.username, # getattr(user, "username", None)
                text=text,
            )
        ticket = await support_service.create_ticket(ticket_data=internal)

    except TicketAlreadyOpen as exc:
        await state.clear()
        return await send_or_edit(
            message,
            f"⚠️ У вас уже есть открытый тикет #{exc.ticket_id}. "
            "Дождитесь ответа поддержки.",
        )

    await state.clear()
    await send_or_edit(
        message,
        f"✅ Обращение принято! Номер тикета: #{ticket.id}. Мы свяжемся с вами как можно скорее."
    )
    # await message.answer("✅ Обращение принято. Мы ответим здесь.")

    notification_text = _render_admin_ticket_message(ticket, user) # (ticket.id, user, text)
    return await _notify_admins(message.bot, admin_ids, notification_text, ticket.id)




