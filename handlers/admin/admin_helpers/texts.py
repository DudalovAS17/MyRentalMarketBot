from schemas.rental import RentalAdminDetailsOut

def format_user_line(label: str, user) -> str:
    """Сформировать строку пользователя для карточки заявки"""
    if not user:
        return f"{label}: <i>не найден</i>"
    tg = user.telegram_id
    username = user.username
    return f"{label}: id={user.id}, tg={tg}, @{username}"

def format_deal_details(details: RentalAdminDetailsOut) -> str:
    """Сформировать текст карточки заявки для админки"""
    r = details.rental
    item = details.item
    client = details.user

    item_title = item.title or f"item_id={r.item_id}"
    status_val = r.status.value

    return (
        f"🧾 <b>Заявка #{r.id}</b>\n\n"
        f"• Статус: <b>{status_val}</b>\n"
        f"• Товар: <b>{item_title}</b>\n"
        f"• Период: {r.rental_period_text or '—'}\n"
        f"• Расчётная стоимость: {r.total_price or '—'}\n"
        f"• Финальная стоимость: {r.final_price or '—'}\n\n"
        f"{format_user_line('👤 Клиент', client)}\n"
        f"☎️ Телефон: {r.client_phone or '—'}\n"
        f"💬 Комментарий клиента: {r.client_comment or '—'}\n"
        f"📝 Комментарий менеджера: {r.manager_comment or '—'}\n"
    )