# Константы callback-данных
CAT_FI_PREFIX = "cat_for_item:"
SUBCAT_FI_PREFIX = "subcat_for_item:"

BACK_TO_MENU_CB = "back_to_main_menu" # "back_to_menu"
ALL_CATEGORY_CB = "all_cat"

BACK_TO_CAT = "back_to_categories"
ADD_ITEM_CB = "add_item"
SHOW_ITEM_CB = "show_item:"
MY_ITEMS_PREFIX = "my_items"

"""Рекомендованное правило для проекта

1) ServiceError (ожидаемая ошибка)
пользователю: коротко
лог: logger.warning(...) (обычно без exc_info=True)

2) Любая “неожиданная” ошибка (Exception)
не ловим в хендлере
глобальный error middleware логирует stacktrace и показывает общий текст пользователю
"""

# tg_user_id = event.from_user.id
# logger.error(f"Ошибка при показе деталей объявления:", exc_info=True)
# logger.error(f"Ошибка при получении объявлений: {e}", exc_info=True)
# очищаем только данные (без сброса FSM) - await state.update_data({})
# print(">>> FSM ACTIVE:", await state.get_state())

# Логика "возврат на шаг названия вещи, а не в меню!" - Убрана!