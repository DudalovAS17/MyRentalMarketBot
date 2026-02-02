from aiogram import Router

from .menu import admin_menu_router # /admin + главное меню админа
from .deals import admin_deals_router # админ по сделкам (твой текущий файл)
from .support import admin_support_router # тикеты поддержки
from .items import admin_items_router # модерация объявлений
from .users import admin_users_router # пользователи / бан / ограничения
#     disputes.py          # жалобы/споры (если отдельно от deals)


admin_router = Router()
admin_router.include_router(admin_menu_router)
admin_router.include_router(admin_deals_router)
admin_router.include_router(admin_support_router)
admin_router.include_router(admin_items_router)
admin_router.include_router(admin_users_router)