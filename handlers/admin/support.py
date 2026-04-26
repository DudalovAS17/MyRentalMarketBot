import logging
from datetime import datetime

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from db.models.support_ticket import SupportTicketStatus
from keyboards.admin_kb import (
    get_admin_support_list_keyboard,
    get_admin_support_ticket_keyboard,
    get_admin_support_menu_kb,
)
from services.admin_service import AdminActionService
from services.support_service import SupportService
from states.support_ticket import SupportStates
from states.admin_support import AdminSupportStates
from utils.functions import send_or_edit

logger = logging.getLogger(__name__)

admin_support_router = Router()

"""
✅ Definition of Done (проверка за 2 минуты)
        Пользователь пишет /support → бот просит текст → создаётся тикет → “принято”
        Всем админам прилетает сообщение с кнопками “Открыть/Ответить/Закрыть”
        Админ: “Открыть” → видит карточку
        Админ: “Ответить” → пишет → пользователю приходит сообщение
        Админ: “Закрыть” → пользователю приходит уведомление + тикет исчезает из open-списка
"""

def _format_datetime(dt: datetime | None) -> str: # ("%d.%m %H:%M")
    if not dt:
        return "—"
    return dt.strftime("%d.%m.%Y %H:%M")

def _format_ticket_card(ticket, user) -> str: # (ticket_id: int, user, text: str)
    tg_id = getattr(user, "telegram_id", None)
    username = getattr(user, "username", None)  # "—"
    #created = _format_datetime(getattr(ticket, "created", None))
    created = datetime.now().strftime("%d.%m.%Y %H:%M")
    return (
        f"🆘 🎫 <b>Тикет поддержки </b> #{ticket.id}\n\n"
        f"💬 <b>Username:</b> {username}\n\n"
        f"Статус: <b>{ticket.status}</b>\n"
        f"👤 <b>Пользователь:</b> @{username} (🆔 tg_id={tg_id})\n"
        f"📅 <b>Создан:</b> 🕒 {created}\n\n"
        f"📝 <b>Текст:</b>\n{ticket.text}"
    )

@admin_support_router.callback_query(F.data == "admin:support")
async def admin_support_list(callback: CallbackQuery, support_service: SupportService) -> None:
    """Меню поддержки в админке."""
    await callback.answer()
    await _show_support_ticket_list(callback, support_service, page=1)

#@admin_support_router.callback_query(F.data == "admin:support:open")
#async def admin_support_open_list(callback: CallbackQuery, state: FSMContext, support_service: SupportService, user):
#    """Открытые тикеты (страница 1)."""
#    await state.clear()
#    await _render_open_list(callback, support_service, page=1)
#    await callback.answer()

@admin_support_router.callback_query(F.data.startswith("admin:support:page:"))
async def admin_support_list_page(callback: CallbackQuery, support_service: SupportService) -> None:
    try:
        page = int(callback.data.split(":")[-1])
    except Exception:
        page = 1
    await _show_support_ticket_list(callback, support_service, page=page)
    await callback.answer()


async def _show_support_ticket_list(event: CallbackQuery, support_service: SupportService, page: int) -> None:
    tickets, has_next = await support_service.list_open_tickets(page)
    lines = [f"📭 <b>Открытые тикеты</b> (стр. {page})\n"]

    if not tickets:
        lines.append("Пока нет открытых тикетов.")
    else:
        for ticket in tickets:
            created = getattr(ticket, "created_at", None)
            created_at = _format_datetime(created)
            uname = f"@{ticket.username}" if ticket.username else f"tg_id={str(ticket.telegram_id)}"
            lines.append(f"•🎫• <b>#{ticket.id}</b> — {uname} — {created_at}")

    text = "\n".join(lines)
    rows = [{"ticket": ticket} for ticket in tickets]
    kb = get_admin_support_list_keyboard(rows, page=page, has_next=has_next) # tickets
    await send_or_edit(event, text, kb)
# get_admin_support_menu_kb()


@admin_support_router.callback_query(F.data.startswith("admin:support:view:"))
async def admin_support_view(callback: CallbackQuery, support_service: SupportService, user) -> None:
    """Показывает карточку тикета поддержки."""
    await callback.answer()
    ticket_id = int(callback.data.split(":")[-1])
    ticket = await support_service.get_ticket_by_id(ticket_id)

    if not ticket:
        await send_or_edit(callback, f"❌ Тикет #{ticket_id} не найден.", None)
        await callback.answer()
        return

    text = _format_ticket_card(ticket, user)
    status_value = (
        ticket.status.value
        if hasattr(ticket.status, "value")
        else str(ticket.status)
    )
    kb = get_admin_support_ticket_keyboard(ticket.id, status_value) # get_admin_ticket_kb
    await send_or_edit(callback, text, markup=kb)
    await callback.answer()


@admin_support_router.callback_query(F.data.startswith("admin:support:reply:"))
async def admin_support_reply_prompt(
    callback: CallbackQuery,
    state: FSMContext,
    support_service: SupportService,
):
    await callback.answer()
    ticket_id = int(callback.data.split(":")[-1])
    ticket = await support_service.get_ticket_by_id(ticket_id)

    if not ticket:
        await send_or_edit(callback, f"❌ Тикет #{ticket_id} не найден.", None)
        await callback.answer()
        return

    if ticket.status != SupportTicketStatus.OPEN:
        await send_or_edit(callback, f"⚠️ Тикет #{ticket_id} уже закрыт.", None)
        await callback.answer()
        return

    await state.set_state(AdminSupportStates.waiting_reply_text)
    await state.update_data(ticket_id=ticket_id)
    await send_or_edit(callback, f"✉️ Введите ответ для тикета #{ticket_id}:", None)
    await callback.answer()

@admin_support_router.message(AdminSupportStates.waiting_reply_text, F.text)
async def admin_support_reply_send(
    message: Message,
    state: FSMContext,
    support_service: SupportService,
    admin_service: AdminActionService,
    user,
):
    """Отправка ответа пользователю + audit."""
    data = await state.get_data()
    ticket_id = int(data.get("ticket_id"))

    if not ticket_id:
        await state.clear()
        return await send_or_edit(message, "⚠️ Не удалось определить тикет. Попробуйте снова.")

    ticket = await support_service.get_ticket_by_id(ticket_id)
    if not ticket:
        await state.clear()
        return await send_or_edit(message, f"❌ Тикет #{ticket_id} не найден.")


    if ticket.status != SupportTicketStatus.OPEN:
        await state.clear()
        return await send_or_edit(message, f"⚠️ Тикет #{ticket_id} уже закрыт.")

    reply_text = (message.text or "").strip()
    if not reply_text:
        return await send_or_edit(message, "❌ Ответ не может быть пустым. Введите текст:")

    # 1️⃣ Отправляем ответ пользователю
    await message.bot.send_message(
        chat_id=int(ticket.telegram_id),
        text=(
            f"💬 <b>Ответ поддержки</b> по тикету #{ticket.id}:\n\n"
            f"{reply_text}"
        ),
        parse_mode="HTML",
    )

    # 2️⃣ Фиксируем активность админа по тикету
    await support_service.mark_admin_replied(ticket_id=ticket.id)

    # 3️⃣ Audit log
    await admin_service.log_action(
        admin_id=int(user.telegram_id),
        action_type="SUPPORT_REPLY",
        entity_type="support_ticket",
        entity_id=ticket.id,
        payload={
            "text": reply_text,
            "to_telegram_id": int(ticket.telegram_id),
        },
    )

    await state.clear()
    return await send_or_edit(message, f"✅ Ответ отправлен пользователю. Тикет #{ticket.id}.") # остаётся открытым.


@admin_support_router.callback_query(F.data.startswith("admin:support:close:"))
async def admin_support_close(
    callback: CallbackQuery,
    support_service: SupportService,
    admin_service: AdminActionService,
    user,
):
    """Закрытие тикета (без причины в MVP)"""
    ticket_id = int(callback.data.split(":")[-1])
    ticket = await support_service.get_ticket_by_id(ticket_id)
    if not ticket:
        await send_or_edit(callback, f"❌ Тикет #{ticket_id} не найден.", None)
        await callback.answer()
        return
        #await callback.answer("Тикет не найден", show_alert=True) - либо так везде можно
        #return

    if ticket.status != SupportTicketStatus.OPEN:
        await send_or_edit(callback, f"⚠️ Тикет #{ticket_id} уже закрыт.", None)
        await callback.answer()
        return

    # 1️⃣ Закрываем тикет
    closed = await support_service.close_ticket_by_admin(ticket_id=ticket_id, admin_tg_id=)
    if not closed:
        await send_or_edit(callback, f"⚠️ Не удалось закрыть тикет #{ticket_id}.", None)
        await callback.answer()
        return

    # 2️⃣ Уведомляем пользователя
    await callback.bot.send_message(
        chat_id=int(ticket.telegram_id),
        text=(
            f"✅ Ваш тикет поддержки #{ticket.id} закрыт. "
            "Если у вас остались вопросы, вы можете создать новый тикет командой /support."
        ),
        parse_mode="HTML",
    )

    # 3️⃣ Audit log
    await admin_service.log_action(
        admin_id=int(user.telegram_id),
        action_type="SUPPORT_CLOSE",
        entity_type="support_ticket",
        entity_id=ticket.id,
        payload={"to_telegram_id": int(ticket.telegram_id)},
    )

    # 4️⃣ Перерисовываем карточку тикета
    updated_ticket = await support_service.get_ticket_by_id(ticket_id) or ticket

    text = _format_ticket_card(updated_ticket, user)
    status_value = (
        updated_ticket.status.value
        if hasattr(updated_ticket.status, "value")
        else str(updated_ticket.status)
    )
    kb = get_admin_support_ticket_keyboard(updated_ticket.id, status_value)

    await send_or_edit(callback, text, markup=kb)
    await callback.answer()