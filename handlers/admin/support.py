from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from services.admin_service import AdminActionService
from services.admin_directory_service import AdminDirectoryService
from services.user_service import UserService
from services.support_service import SupportService
from services.notif_service import NotificationService
from .admin_helpers.show import show_support_ticket_list, show_support_ticket_card_or_not_found
from .admin_helpers.parse import parse_support_page, parse_support_ticket_id
from .admin_helpers.texts import format_ticket_card

from .admin_helpers.file_support import (load_open_support_ticket_or_notify, send_support_reply_and_audit,
                                         notify_ticket_closed_and_audit)
from .admin_helpers.keyboard import get_admin_support_ticket_keyboard
from states.admin_support import AdminSupportStates
from utils.functions import send_or_edit

admin_support_router = Router()

# ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
@admin_support_router.callback_query(F.data == "admin:support")
async def admin_support_list(callback: CallbackQuery, support_service: SupportService, user_service: UserService) -> None:
    """Меню поддержки в админке"""
    await callback.answer()

    await show_support_ticket_list(callback, user_service, support_service, page=1)

# @admin_support_router.callback_query(F.data == "admin:support:open")
# async def admin_support_open_list(callback: CallbackQuery, state: FSMContext, support_service: SupportService, user):
#     """Открытые тикеты (страница 1)"""
#     await callback.answer()
#
#     await state.clear()
#     await render_open_list(callback, support_service, page=1)


@admin_support_router.callback_query(F.data.startswith("admin:support:page:"))
async def admin_support_list_page(callback: CallbackQuery, support_service: SupportService, user_service: UserService) -> None:
    """Показать выбранную страницу списка открытых тикетов поддержки."""
    await callback.answer()

    page = parse_support_page(callback.data)
    await show_support_ticket_list(callback, user_service, support_service, page=page)


@admin_support_router.callback_query(F.data.startswith("admin:support:view:"))
async def admin_support_view(callback: CallbackQuery, support_service: SupportService, user_service: UserService) -> None:
    """Показывает карточку тикета поддержки"""
    await callback.answer()

    ticket_id = parse_support_ticket_id(callback.data)
    if ticket_id is None:
        #await callback.answer("Некорректный ID", show_alert=True)
        return

    await show_support_ticket_card_or_not_found(callback, user_service, support_service, ticket_id)

# ────────────────────────────────────────── Ответа на тикет ───────────────────────────────────────────────────────────
@admin_support_router.callback_query(F.data.startswith("admin:support:reply:"))
async def admin_support_reply_prompt(callback: CallbackQuery, state: FSMContext, support_service: SupportService):
    """Запросить текст ответа на тикет"""
    await callback.answer()

    ticket_id = parse_support_ticket_id(callback.data)
    if ticket_id is None:
        #await callback.answer("Некорректный ID", show_alert=True)
        return

    ticket = await load_open_support_ticket_or_notify(callback, support_service, ticket_id)
    if ticket is None:
        return

    await state.set_state(AdminSupportStates.waiting_reply_text)
    await state.update_data(ticket_id=ticket_id)

    await send_or_edit(callback, f"✉️ Введите ответ для тикета #{ticket_id}:", None)


@admin_support_router.message(AdminSupportStates.waiting_reply_text, F.text)
async def admin_support_reply_send(
    message: Message,
    state: FSMContext,
    support_service: SupportService,
    admin_service: AdminActionService,
    user_service: UserService,
    notification_service: NotificationService,
) -> None:
    """Отправка ответа пользователю + audit"""
    data = await state.get_data()

    ticket_id = int(data.get("ticket_id"))
    if not ticket_id:
        await state.clear()
        await send_or_edit(message, "⚠️ Не удалось определить тикет. Попробуйте снова.")
        return

    ticket = await load_open_support_ticket_or_notify(message, support_service, ticket_id)
    if ticket is None:
        await state.clear()
        return

    reply_text = (message.text or "").strip()
    if not reply_text:
        await send_or_edit(message, "❌ Ответ не может быть пустым. Введите текст:")
        return

    ticket_user = await user_service.get_by_id(ticket.user_id)
    if ticket_user is None:
        await state.clear()
        await send_or_edit(message, f"❌ Пользователь тикета #{ticket.id} не найден.")
        return

    # 1️⃣ Отправляем ответ пользователю и Audit log
    delivered = await send_support_reply_and_audit(message, admin_service, notification_service, ticket_user, ticket, reply_text)
    if not delivered:
        await state.clear()
        await send_or_edit(message, f"⚠️ Ответ не доставлен пользователю. Тикет #{ticket.id} не помечен как отвеченный.")
        return

    # 2️⃣ Фиксируем активность админа по тикету только после успешной доставки
    await support_service.mark_admin_replied(ticket_id=ticket.id)

    await state.clear()
    await send_or_edit(message, f"✅ Ответ отправлен пользователю. Тикет #{ticket.id}.") # остаётся открытым.


# ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
#admin_tg_id=callback.from_user.id или admin_tg_id=int(user.telegram_id)
@admin_support_router.callback_query(F.data.startswith("admin:support:close:"))
async def admin_support_close(
        callback: CallbackQuery,
        support_service: SupportService,
        admin_service: AdminActionService,
        admin_directory_service: AdminDirectoryService,
        user_service: UserService,
        notification_service: NotificationService,
) -> None:
    """Закрытие тикета (без причины в MVP)"""
    await callback.answer()

    ticket_id = parse_support_ticket_id(callback.data)
    if ticket_id is None:
        # await callback.answer("Некорректный ID", show_alert=True)
        return

    ticket = await load_open_support_ticket_or_notify(callback, support_service, ticket_id)
    if ticket is None:
        return

    ticket_user = await user_service.get_by_id(ticket.user_id)
    if ticket_user is None:
        await send_or_edit(callback, f"❌ Пользователь тикета #{ticket_id} не найден.", None)
        return

    admin = await admin_directory_service.get_by_telegram_id(callback.from_user.id)
    if admin is None:
        await send_or_edit(callback, "❌ Профиль сотрудника не найден в таблице admins.", None)
        return

    # Закрываем тикет
    closed = await support_service.close_ticket_by_admin(ticket_id=ticket_id, closed_by_admin_id=admin.id)
    if not closed:
        await send_or_edit(callback, f"⚠️ Не удалось закрыть тикет #{ticket_id}.", None)
        return

    # Уведомляем пользователя и Audit log
    delivered = await notify_ticket_closed_and_audit(
        callback=callback,
        admin_service=admin_service,
        notification_service=notification_service,
        ticket_user = ticket_user,
        ticket=ticket,
        admin_tg_id=callback.from_user.id,
    )

    # Перерисовываем карточку тикета
    updated_ticket = await support_service.get_ticket_by_id(ticket_id) or ticket

    await send_or_edit(
        callback,
        (("⚠️ Тикет закрыт, но пользователя не удалось уведомить.\n\n" if not delivered else "") + format_ticket_card(
            updated_ticket)), # format_ticket_card(updated_ticket),
        get_admin_support_ticket_keyboard(updated_ticket.id, updated_ticket.status)
    )