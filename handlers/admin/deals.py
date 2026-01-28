from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from states.admin import AdminStates
from keyboards.admin_kb import (
    get_admin_deals_list_keyboard,
    get_admin_deal_details_keyboard,
    get_admin_dispute_target_keyboard
)

from utils.functions import send_or_edit
from services.admin_rental_service import AdminRentalService

admin_deals_router = Router()

"""
Админ должен уметь:
    - увидеть последние сделки (пагинация)
    - открыть конкретную сделку (по кнопке из списка и по ID)
    - увидеть детали (участники, предмет, даты, статус)
    - выполнить админ-действия (минимум: cancel + resolve dispute), строго по whitelist

admin:deals — вход в раздел | 🔙 К списку
admin:deals:page:<n> — пагинация (⬅️ Пред | ➡️ След)
admin:deals:view:<rental_id> — 🔎 Открыть карточку сделки | 🔄 Обновить
admin:deals:by_id — 🔎 Открыть по ID
admin:deals:action:<rental_id>:<action> — действие админа

admin:menu — 🔙 Назад в админ-меню

admin:deals:resolve:{rental_id} - ✅ Закрыть спор
admin:deals:cancel:{rental_id} - 🚫 Отменить сделку


✅ Раздел “Сделки” в админке
✅ Список последних сделок (пагинация)
✅ Открытие сделки по кнопке
✅ Открытие сделки по ID (FSM)
✅ Отмена сделки с причиной (FSM) + лог в admin_actions
✅ Закрытие спора (только если DISPUTED) + лог в admin_actions
✅ Безопасная модель действий (whitelist условий)

Экран 1: “Последние сделки”
    Список 5–10 штук:
        #ID | статус | предмет | даты
    Кнопки:
        Открыть #123
        ➡️ След / ⬅️ Пред (если надо)
        🔎 Открыть по ID
        🔙 Назад в админ-меню

Экран 2: “Карточка сделки”
    Текст:
        Rental ID
        статус
        item (название)
        owner / renter (id, username)
        start/end
        created_at
    Кнопки:
        🚫 Отменить (просит причину)
        ✅ Закрыть спор (если в dispute)
        🔄 Обновить
        🔙 Назад к списку

Whitelist переходов (админские действия должны быть “безопасными”, чтобы не сломать логику аренды):
    cancel - разрешено (если статус не COMPLETED/CANCELLED)
    resolve_dispute - только если статус DISPUTE

Audit Log - каждое админ-действие логируем:
    admin_id
    action_type (CANCEL_RENTAL, RESOLVE_DISPUTE)
    entity (rental, rental_id)
    payload (reason/resolution)
    created_at
"""

async def _show_deals_list(
        event: Message | CallbackQuery,
        admin_rental_service: AdminRentalService,
        state: FSMContext,
        page: int
):
    rows, has_next = await admin_rental_service.list_recent_rentals(page=page)
    await state.update_data(admin_deals_page=page)

    lines = [f"📄 <b>Сделки (последние), стр. {page}</b>\n"]

    if not rows:
        lines.append("Пока нет сделок.")
        text = "\n".join(lines)
        kb = get_admin_deals_list_keyboard([], page=page, has_next=False)
        await send_or_edit(event, text, kb)
        return

    for row in rows:
        r = row["rental"]
        item = row["item"]
        item_title = getattr(item, "title", None) or getattr(item, "name", None) or f"item_id={r.item_id}"
        status_val = getattr(r.status, "value", str(r.status))
        lines.append(f"• <b>#{r.id}</b> — {status_val} — {item_title}")

    text = "\n".join(lines)
    kb = get_admin_deals_list_keyboard(rows, page=page, has_next=has_next)
    await send_or_edit(event, text, kb)

@admin_deals_router.callback_query(F.data == "admin:deals")
async def admin_deals_list(
        callback: CallbackQuery,
        state: FSMContext,
        admin_rental_service: AdminRentalService,
        #user
):
    """Список последних сделок (страница 1)."""
    #await state.clear()
    await _show_deals_list(callback, admin_rental_service, state, page=1)
    await callback.answer()

@admin_deals_router.callback_query(F.data.startswith("admin:deals:page:"))
async def admin_deals_page(
        callback: CallbackQuery,
        state: FSMContext,
        admin_rental_service: AdminRentalService,
        #user
):
    """Пагинация списка сделок."""
    try:
        page = int(callback.data.split(":")[-1])
    except Exception:
        page = 1

    await _show_deals_list(callback, admin_rental_service, state, page=page)
    await callback.answer()


def _format_user_line(label: str, u) -> str:
    if not u:
        return f"{label}: <i>не найден</i>"
    tg = getattr(u, "telegram_id", None)
    username = getattr(u, "username", None)
    return f"{label}: id={u.id}, tg={tg}, @{username}"

def _format_deal_details(data: dict) -> str:
    r = data["rental"]
    item = data["item"]

    owner = data["owner"]
    renter = data["renter"]

    item_title = getattr(item, "title", None) or getattr(item, "name", None) or f"item_id={r.item_id}"
    status_val = getattr(r.status, "value", str(r.status))

    return (
        f"🧾 <b>Сделка #{r.id}</b>\n\n"
        f"• Статус: <b>{status_val}</b>\n"
        f"• Предмет: <b>{item_title}</b>\n"
        f"• Даты: {r.start_date} → {r.end_date}\n\n"
        f"{_format_user_line('👤 Владелец', owner)}\n"
        f"{_format_user_line('🧑‍💼 Арендатор', renter)}\n"
    )

@admin_deals_router.callback_query(F.data.startswith("admin:deals:view:"))
async def admin_deals_view(
        callback: CallbackQuery,
        admin_rental_service: AdminRentalService,
        #user
):
    """Карточка конкретной сделки."""
    try:
        rental_id = int(callback.data.split(":")[-1])
    except Exception:
        await callback.answer("Некорректный ID", show_alert=True)
        return

    data = await admin_rental_service.get_details(rental_id)
    if not data:
        await send_or_edit(callback, f"❌ Сделка #{rental_id} не найдена.", None)
        await callback.answer()
        return

    r = data["rental"]
    status_val = getattr(r.status, "value", str(r.status))
    text = _format_deal_details(data)
    kb = get_admin_deal_details_keyboard(rental_id=rental_id, status_value=status_val)

    await send_or_edit(callback, text, kb)
    await callback.answer()


@admin_deals_router.callback_query(F.data == "admin:deals:by_id") # 🔎 Открыть по ID
async def admin_deals_open_by_id(
        callback: CallbackQuery,
        state: FSMContext,
        #user
):
    """Просим админа ввести ID сделки."""
    await state.set_state(AdminStates.waiting_rental_id)
    await send_or_edit(callback, "Введите ID сделки (число):", None)
    await callback.answer()

@admin_deals_router.message(AdminStates.waiting_rental_id)
async def admin_deals_process_id(
        message: Message,
        state: FSMContext,
        admin_rental_service: AdminRentalService,
        #user
):
    """Обработка введенного ID сделки."""
    raw = (message.text or "").strip()
    if not raw.isdigit():
        await message.answer("❌ Нужно число. Введите ID сделки:")
        return

    rental_id = int(raw)
    await state.clear()

    data = await admin_rental_service.get_details(rental_id)
    if not data:
        await message.answer(f"❌ Сделка #{rental_id} не найдена.")
        return

    r = data["rental"]
    status_val = getattr(r.status, "value", str(r.status))
    text = _format_deal_details(data)
    kb = get_admin_deal_details_keyboard(rental_id=rental_id, status_value=status_val)

    await send_or_edit(message, text, kb)

@admin_deals_router.callback_query(F.data.startswith("admin:deals:cancel:")) # 🚫 Отменить сделку
async def admin_deals_cancel_ask(
        callback: CallbackQuery,
        state: FSMContext,
        #user
):
    """Запрос причины отмены."""
    rental_id = int(callback.data.split(":")[-1])
    await state.set_state(AdminStates.waiting_cancel_reason)
    await state.update_data(rental_id=rental_id)
    await send_or_edit(callback, f"🚫 Укажите причину отмены сделки #{rental_id}:", None)
    await callback.answer()

@admin_deals_router.message(AdminStates.waiting_cancel_reason)
async def admin_deals_cancel_apply(
        message: Message,
        state: FSMContext,
        admin_rental_service: AdminRentalService,
        user
):
    data = await state.get_data()
    rental_id = data.get("rental_id")
    reason = (message.text or "").strip()

    if not reason:
        await message.answer("❌ Причина не может быть пустой. Введите текст причины:")
        return

    await state.clear()

    ok = await admin_rental_service.admin_cancel_rental(rental_id=int(rental_id), admin_id=user.telegram_id, reason=reason)
    if not ok:
        await message.answer("❌ Нельзя отменить эту сделку (возможно, уже завершена или не найдена).")
        return

    details = await admin_rental_service.get_details(int(rental_id))
    text = _format_deal_details(details) if details else f"✅ Сделка #{rental_id} отменена."
    r = details["rental"] if details else None
    status_val = getattr(r.status, "value", "") if r else ""
    kb = get_admin_deal_details_keyboard(rental_id=int(rental_id), status_value=status_val) if details else None

    await send_or_edit(message, "✅ Отменено.\n\n" + text, kb)

@admin_deals_router.callback_query(F.data.startswith("admin:deals:resolve:")) # ✅ Закрыть спор
async def admin_deals_resolve_ask(
        callback: CallbackQuery,
        state: FSMContext,
        #user
):
    """Запрос текста решения по спору."""
    rental_id = int(callback.data.split(":")[-1])
    await state.set_state(AdminStates.waiting_dispute_resolution)
    await state.update_data(rental_id=rental_id)
    await send_or_edit(callback, f"✅ Введите решение по спору сделки #{rental_id} (кратко):", None)
    await callback.answer()

@admin_deals_router.message(AdminStates.waiting_dispute_resolution)
async def admin_deals_resolve_collect_resolution(
        message: Message,
        state: FSMContext,
        #user
):
    data = await state.get_data()
    rental_id = int(data.get("rental_id"))
    resolution = (message.text or "").strip()

    if not resolution:
        await message.answer("❌ Решение не может быть пустым. Введите текст:")
        return

    await state.set_state(AdminStates.waiting_dispute_target)
    await state.update_data(resolution=resolution)

    kb = get_admin_dispute_target_keyboard(rental_id)
    await send_or_edit(
        message,
        f"Выберите исход закрытия спора по сделке #{rental_id}.\n\n"
        f"📝 Решение:\n{resolution}",
        kb,
        parse_mode="HTML",
    )

@admin_deals_router.callback_query(F.data.startswith("admin:deals:resolve_target:"))
async def admin_deals_resolve_apply_target(
        callback: CallbackQuery,
        state: FSMContext,
        admin_rental_service: AdminRentalService,
        user
):
    parts = (callback.data or "").split(":")
    if len(parts) < 5:
        await callback.answer("Некорректные данные", show_alert=True)
        return

    rental_id = int(parts[3])
    target = parts[4]

    data = await state.get_data()
    resolution = (data.get("resolution") or "").strip()
    if not resolution:
        await callback.answer("Сначала введите текст решения.", show_alert=True)
        return

    from db.models.rental import RentalStatus
    target_map = {
        "active": RentalStatus.ACTIVE,
        "completed": RentalStatus.COMPLETED,
        "confirmed": RentalStatus.CONFIRMED,
    }
    if target not in target_map:
        await callback.answer("Некорректный исход", show_alert=True)
        return

    ok = await admin_rental_service.admin_resolve_dispute(
        rental_id=rental_id,
        admin_id=user.telegram_id,
        resolution=resolution,
        target_status=target_map[target],
    )

    await state.clear()

    if not ok:
        await callback.answer("Нельзя закрыть спор (проверь статус/сделку).", show_alert=True)
        return

    details = await admin_rental_service.get_details(rental_id)
    if not details:
        await send_or_edit(callback, f"✅ Спор закрыт. Сделка #{rental_id}.", None)
        await callback.answer()
        return

    r = details["rental"]
    status_val = getattr(r.status, "value", str(r.status))
    text = _format_deal_details(details)
    kb = get_admin_deal_details_keyboard(rental_id=rental_id, status_value=status_val)

    await send_or_edit(callback, "✅ Спор закрыт.\n\n" + text, kb, parse_mode="HTML")
    await callback.answer()
