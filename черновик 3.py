#Сейчас show_item_details по id — важно, чтобы пользователь не мог открыть чужое
# (если кто-то подменит callback). Это часть MVP безопасности.










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