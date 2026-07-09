from typing import Optional
from aiogram.types import CallbackQuery


async def parse_int_id_from_callback(
    callback: CallbackQuery,
    index: int = 1,
    error_text: str = "Некорректные данные",
) -> Optional[int]:
    """
    Достаёт int ID из callback.data вида 'prefix:123'.
    При ошибке сам отвечает пользователю и возвращает None.
    """
    parts = callback.data.split(":")
    if len(parts) <= index:
        await callback.answer(error_text, show_alert=True)
        return None

    try:
        return int(parts[index])
    except ValueError:
        await callback.answer(error_text, show_alert=True)
        return None


# ──────────────────────────────────────────── BASE HANDLER ────────────────────────────────────────────────────────────
BACK_TO_MENU_CB = "back_to_main_menu" # "back_to_menu"

# ──────────────────────────────────────────── CATEGORY HANDLER ────────────────────────────────────────────────────────
CAT_CB_PREFIX = "cat:"
SUBCAT_CB_PREFIX = "subcat:"
ITEM_DETAILS_CB = "show_item_details:"
SHOW_ALL_PHOTOS_CB = "show_all_photos:"
BACK_TO_CAT = "back_to_categories" # show_categories()
CAROUSEL_NAV_CB = "subcat_items_nav:"
PHOTO_NAV_CB = "item_photo_nav:" # Логика N1

# ───────────────────────────────────────────── ADMIN HANDLER ──────────────────────────────────────────────────────────
BACK_TO_ADMIN_MENU_CB = "menu:main" # "admin:menu" / admin_menu

# create item
ADMIN_CAT_FI_PREFIX = "cat_for_item:"
ADMIN_SUBCAT_FI_PREFIX = "subcat_for_item:"
ADMIN_ADD_ITEM_CB = "add_item"
ADMIN_PUBLISH_ITEM_CB = "publish_item:"
ADMIN_CANCEL_ITEM_CB = "cancel_item:"
ADMIN_MAX_PHOTOS = 5
ADMIN_CREATE_ITEM_MODE = "create_item"

# deals
DEALS_PREFIX = "admin:deals"
DEALS_NEW_PREFIX = "admin:deals:new"
DEALS_ALL_PREFIX = "admin:deals:all"
DEALS_PAGE_PREFIX = "admin:deals:page:"
DEALS_NEW_PAGE_PREFIX = "admin:deals:new:page:"
DEALS_VIEW_PREFIX = "admin:deals:view:"
DEALS_BY_ID_PREFIX = "admin:deals:by_id"

# deals status actions
DEALS_PROGRESS_PREFIX = "admin:deals:progress:"
DEALS_CONFIRM_PREFIX = "admin:deals:confirm:"
DEALS_REJECT_PREFIX = "admin:deals:reject:"
DEALS_COMPLETE_PREFIX = "admin:deals:complete:"
DEALS_CANCEL_PREFIX = "admin:deals:cancel:"
DEALS_COMMENT_PREFIX = "admin:deals:comment:"
DEALS_CONTACT_PREFIX = "admin:deals:contact:"

# items moderation
ADMIN_ITEMS_MOD = "admin:items"
ADMIN_ITEMS_MOD_FILTER = "admin:items:filter:"
ADMIN_ITEMS_MOD_PAGE = "admin:items:page:"
ADMIN_ITEMS_MOD_VIEW = "admin:items:view:"
ADMIN_ITEMS_MOD_APPROVE = "admin:items:approve:"
ADMIN_ITEMS_MOD_HIDE = "admin:items:hide:"
ADMIN_ITEMS_MOD_UNHIDE = "admin:items:unhide:"
ADMIN_ITEMS_MOD_ARCHIVE = "admin:items:archive:"

# support
ADMIN_SUPPORT = "admin:support"
ADMIN_SUPPORT_ITEMS = "admin:support:items"
ADMIN_SUPPORT_RENTALS = "admin:support:rentals"
ADMIN_SUPPORT_GENERAL = "admin:support:general"
ADMIN_SUPPORT_PAGE = "admin:support:page:"
ADMIN_SUPPORT_VIEW = "admin:support:view:"
ADMIN_SUPPORT_REPLY = "admin:support:reply:"
ADMIN_SUPPORT_CLOSE = "admin:support:close:"
ADMIN_SUPPORT_OPEN = "admin:support:open:"

# update item
ADMIN_EDIT_ITEM_CB = "edit_item:"

# users moderation
ADMIN_USERS_MOD = "admin:users"
ADMIN_USERS_MOD_VIEW = "admin:users:view"
ADMIN_USERS_MOD_FIND = "admin:users:find"
ADMIN_USERS_MOD_BAN = "admin:users:ban:"
ADMIN_USERS_MOD_UNBAN = "admin:users:unban:"

ADMIN_CONTENT = "admin:content" # - "Контент/FAQ"

ADMIN_EXIT_PREFIX = "admin:exit"

# ────────────────────────────────────────────── AUTH HANDLER ──────────────────────────────────────────────────────────
# profile
PROFILE_STATS = "profile_stats"
PROFILE_ACHIEVEMENTS = "profile_achievements"
PROFILE_BACK = "back_to_profile"

# settings
PROFILE_SETTINGS = "profile_settings"
PROFILE_BACK_TO_SETTINGS = "back_to_profile_settings"
PROFILE_NOTIFICATIONS = "profile_notifications" # "settings_notifications"

# privacy
PROFILE_SETTINGS_PRIVACY = "settings_privacy"
PROFILE_PRIVACY_POLICY = "show_privacy_policy"

# edit profile
PROFILE_EDIT_NAME = "edit_profile_field:name"
PROFILE_EDIT_EMAIL = "edit_profile_field:email"
PROFILE_EDIT_PHONE = "profile_change_phone" #"edit_profile_field:phone"
PROFILE_EDIT = "settings_edit_profile"


# ───────────────────────────────────────────── RENTALS HANDLER ────────────────────────────────────────────────────────
# flow create
CONFIRM_RENT_CB = "confirm_rent"
CANCEL_RENT_FLOW_CB = "cancel_rent_flow" # new
RENT_ITEM_CB = "rent_item:"
RENT_PERIOD_CB = "rent_period:"

RENT_QUANTITY_CB = "rent_quantity:"
RENT_DELIVERY_CB = "rent_delivery:"
RENT_BACK_CB = "rent_back"
RENT_USE_PROFILE_NAME_CB = "rent_use_profile_name"
RENT_USE_PROFILE_PHONE_CB = "rent_use_profile_phone"
RENT_SKIP_COMMENT_CB = "rent_skip_comment"
RENT_CHANGE_CB = "rent_change"

# details
MY_RENTALS_CB = "rental_list" # back_to_rentals
RENTAL_DETAILS_CB = "rental_details:"
#BACK_TO_RENTALS = "back_to_rentals"

# actions
CLIENT_CANCEL_RENTAL_CB = "rental_action:canceled_by_client:" # "rental_action:cancel:"


# ──────────────────────────────────────────── SEARCH HANDLER ──────────────────────────────────────────────────────────
SEARCH = "search"

PAGE_SIZE = 8
QUERY_MIN_LEN = 2
QUERY_MAX_LEN = 60
SEARCH_PAGE_CB_PREFIX = "search:page:"
SEARCH_NEW_QUERY_CB = "search:new_query"
SEARCH_BACK_CB = "search:back"

ALL_CATEGORY_CB = "all_cat"
SEARCH_CITY_CB = "search_by_city"
SEARCH_FILTERS_CB = "search_filters"

# ──────────────────────────────────────────── SUPPORT HANDLER ─────────────────────────────────────────────────────────
SUPPORT = "support"

SUPPORT_START = "support:start"
SUPPORT_CANCEL = "support:cancel" # "cancel_support"
SUPPORT_CONTINUE = "support:continue:"
CLIENT_SUPPORT_RENTAL_CB = "rental_action:support_by_client:" # "rental_action:support:"


# ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

# ITEM HANDLER
SHOW_ITEM_CB = "show_item:"


# Есть уже, но оставляю пока на всякий
# CAT_FI_PREFIX = "cat_for_item:"
# SUBCAT_FI_PREFIX = "subcat_for_item:"
# ADD_ITEM_CB = "add_item"
# CREATE_ITEM_MODE = "create_item"
# PUBLISH_ITEM_CB = "publish_item:"
# EDIT_ITEM_CB = "edit_item:"
# CANCEL_ITEM_CB = "cancel_item:"

MAX_PHOTOS = 5

MESSAGE_OWNER_CB = "message_owner:" #?


REVIEWS_CB = "reviews:"


# RENTAL HANDLER
RENTAL_CB = "rentals"
RETURN_CB = "return"
CONFIRM_CB = "confirm"
REVIEW_CB = "review"
DISPUTE_CB = "dispute"
CANCEL_CB = "cancel"
BACK_CB = "back"
ITEM_DETAILS = "item_details:"



IGNORE_CB = "ignore"

START_DATE_DAYS_AHEAD = 5

RENT_PERIOD_CB = "rent_period:"
CUSTOM_RENT_DATES_CB = "rent_dates:custom"
CLIENT_CANCEL_RENTAL_CB = "rental_action:canceled_by_client:" # "rental_action:cancel:"
CLIENT_SUPPORT_RENTAL_CB = "rental_action:support_by_client:" # "rental_action:support:"



"""
Логика поддержки для конкретной аренды = "💬 Написать в поддержку":
CLIENT_SUPPORT_RENTAL_CB = "rental_action:support_by_client:"
rental_support_by_client - Написать в поддержку для клиента
f"{CLIENT_SUPPORT_RENTAL_CB}{rental.id}"
"""
