from aiogram import Router

from .create_item import admin_create_item_router
from .NO_update_item import admin_update_item_router
from .menu import admin_menu_router # /admin + главное меню админа

from .deals import admin_deals_router # админ по заявкам (твой текущий файл)
from .deals_status_actions import admin_status_actions_router # смена статус заявки админом

from .support import admin_support_router # тикеты поддержки
from .items_moderation import admin_items_router # модерация товаров
from .users_moderation import admin_users_router # пользователи / бан / ограничения

from status.admin_status import AdminRole
from utils.admin_access import AdminRoleMiddleware

#     disputes.py # жалобы/споры (если отдельно от deals)

admin_router = Router()


_catalog_guard = AdminRoleMiddleware({AdminRole.ADMIN, AdminRole.OWNER})
for _router in (admin_items_router, admin_create_item_router, admin_update_item_router):
    _router.message.middleware(_catalog_guard)
    _router.callback_query.middleware(_catalog_guard)

_users_guard = AdminRoleMiddleware({AdminRole.ADMIN, AdminRole.OWNER})
admin_users_router.message.middleware(_users_guard)
admin_users_router.callback_query.middleware(_users_guard)


admin_router.include_router(admin_menu_router) # +-
admin_router.include_router(admin_deals_router) # ***** кнопка админки "Заявки на аренду" *****
admin_router.include_router(admin_support_router) # ***** кнопка админки "Обращения клиентов" *****
admin_router.include_router(admin_items_router) # ***** кнопка админки "Модерация товаров" *****
admin_router.include_router(admin_users_router) # ***** кнопка админки "Наши клиенты" *****
admin_router.include_router(admin_status_actions_router) # *****

admin_router.include_router(admin_create_item_router) # ***** кнопка админки "+Создать товар" *****
admin_router.include_router(admin_update_item_router) # -

# Нереализовано ***** кнопка админки "Контент/FAQ" *****