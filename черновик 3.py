#Сейчас show_item_details по id — важно, чтобы пользователь не мог открыть чужое
# (если кто-то подменит callback). Это часть MVP безопасности.




""" Незаконченное
1) Время в TimestampMixin.
    а) server_default=func.timezone("utc", func.now()),
        onupdate=func.timezone("utc", func.now())
    б) server_default=func.now()
        onupdate=func.now()
    с) default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),

2) db/models/user.py
Нужно будет убрать is_admin!
is_admin не хранится в БД, потому что источник истины — settings.admin_ids (Telegram ID),
иначе гарантирован рассинхрон.
"""





# порядок статусов (Сортируем для удобства: сначала активные, потом остальные)
status_order = {}
status_labels = {
    "ACTIVE": "Активная аренда",
    "CONFIRMED": "Подтверждена владельцем",
    "REQUESTED": "Запрос отправлен",
    "COMPLETED": "Завершена",
    "CANCELLED_BY_OWNER": "Отклонена владельцем",
    "CANCELLED_BY_RENTER": "Отменена арендатором",
    "REJECTED_BY_OWNER": "Отменена владельцем (до начала)",
    "REJECTED_BY_RENTER": "Отменена арендатором (до начала)",
    "CANCELLED_CONFIRMED_BY_OWNER": "Отменена владельцем",
    "CANCELLED_CONFIRMED_BY_RENTER": "Отменена арендатором",
    "DISPUTED": "Спор",
}