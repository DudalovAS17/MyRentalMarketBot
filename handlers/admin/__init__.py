from aiogram import Router

from .menu import admin_menu_router
from .deals import admin_deals_router
#     menu.py              # /admin + главное меню админа
#     deals.py             # админ по сделкам (твой текущий файл)
#     items.py             # модерация объявлений
#     users.py             # пользователи / бан / ограничения
#     disputes.py          # жалобы/споры (если отдельно от deals)
#     support.py           # тикеты поддержки

admin_router = Router()
admin_router.include_router(admin_menu_router)
admin_router.include_router(admin_deals_router)