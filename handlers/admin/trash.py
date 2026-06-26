

# ────────────────────────────────────────── Items ─────────────────────────────────────────────────────────────────────
# "admin:items:reject:"
# admin_items_reject_ask - Запрос причины отклонения товара

# AdminStates.waiting_item_reject_reason
# admin_items_reject_apply - Применяет отклонение товара с причиной
# apply_item_status_action

# ────────────
#show_item_details - Показывает детали товара (SHOW_ITEM_CB)


# ────────────────────────────────────────── Create Items ──────────────────────────────────────────────────────────────
""" Старая логика:
start_create_item_from_my_items - Запуск процесса создания объявления из списка 'Мои объявления'
show_subcategories_for_creating_item - Показывает подкатегории для FSM-сценария 'Создать объявление'
start_create_item_from_subcategory - Переход из подкатегории к вводу названия вещи

start_create_item_from_menu Сценарий 1: старт создания объявления из меню без выбора категории/подкатегории
"""


# ────────────────────────────────────── Deals status actions ──────────────────────────────────────────────────────────
""" Удалено:

# 🚫 Отменить сделку
# admin_deals_cancel_ask - Запрос причины отмены (DEALS_CANCEL_PREFIX)

# AdminStates.waiting_rental_cancel_reason) # .waiting_cancel_reason
# admin_deals_cancel_apply - Применить отмену сделки с причиной

# ✅ Закрыть спор
# admin_deals_resolve_ask - Запрос текста решения по спору (DEALS_RESOLVE_PREFIX)

# AdminStates.waiting_rental_resolution / waiting_dispute_resolution
# admin_deals_resolve_collect_resolution - Сохранить текст решения по спору и запросить итоговый статус

# admin_deals_resolve_apply_target - Закрыть спор с выбранным итоговым статусом (DEALS_RESOLVE_TARGET_PREFIX)
"""