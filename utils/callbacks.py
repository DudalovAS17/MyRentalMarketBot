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


RENT_ITEM_CB = "rent_item:"
SHOW_ALL_PHOTOS_CB = "show_all_photos:"
MESSAGE_OWNER_CB = "message_owner:"
REVIEWS_CB = "reviews:"


CANCEL_RENT_FLOW_CB = "cancel_rent_flow"
START_DATE_CB = "start_date:"
CONFIRM_RENT_CB = "confirm_rent"


# Константы callback-данных
# CATEGORY HANDLER
CAT_CB_PREFIX = "cat:"
SUBCAT_CB_PREFIX = "subcat:"
ITEM_DETAILS_CB = "show_item_details:"
CAROUSEL_NAV_CB = "subcat_items_nav:"
SHOW_ALL_PHOTOS_CB = "show_all_photos:"
BACK_TO_CAT = "back_to_categories" # show_categories()

# будут обработаны в хендлере Search
ALL_CATEGORY_CB = "all_cat"
SEARCH_CITY_CB = "search_by_city"
SEARCH_FILTERS_CB = "search_filters"
# где?
BACK_TO_MENU_CB = "back_to_main_menu" # главное меню show_main_menu()


# ITEM HANDLER
CAT_FI_PREFIX = "cat_for_item:"
SUBCAT_FI_PREFIX = "subcat_for_item:"

BACK_TO_MENU_CB = "back_to_main_menu" # "back_to_menu"
ALL_CATEGORY_CB = "all_cat"

BACK_TO_CAT = "back_to_categories"
ADD_ITEM_CB = "add_item"
SHOW_ITEM_CB = "show_item:"
MY_ITEMS_PREFIX = "my_items"

CREATE_ITEM_MODE = "create_item"

PUBLISH_ITEM_CB = "publish_item:"
EDIT_ITEM_CB = "edit_item:"
CANCEL_ITEM_CB = "cancel_item:"

MAX_PHOTOS = 5

# ADMIN CREATE ITEM
ADMIN_CAT_FI_PREFIX = "cat_for_item:"
ADMIN_SUBCAT_FI_PREFIX = "subcat_for_item:"
ADMIN_ADD_ITEM_CB = "add_item"
ADMIN_PUBLISH_ITEM_CB = "publish_item:"
ADMIN_EDIT_ITEM_CB = "edit_item:"
ADMIN_CANCEL_ITEM_CB = "cancel_item:"
ADMIN_MAX_PHOTOS = 5
ADMIN_CREATE_ITEM_MODE = "create_item"


# RENTAL HANDLER
RENTAL_CB = "rentals"
RETURN_CB = "return"
CONFIRM_CB = "confirm"
REVIEW_CB = "review"
DISPUTE_CB = "dispute"
CANCEL_CB = "cancel"
BACK_CB = "back"
ITEM_DETAILS = "item_details:"
RENT_ITEM_CB = "rent_item:"
START_DATE_CB = "start_date:"
END_DATE_CB = "end_date:"
CONFIRM_RENT_CB = "confirm_rent"

BACK_TO_MENU_CB = "back_to_main_menu" # "back_to_menu" # "menu:main"
MY_RENTALS_CB = "rental_list" # back_to_rentals
RENTAL_DETAILS_CB = "rental_details:"
CANCEL_RENT_FLOW_CB = "cancel_rent_flow" # new


IGNORE_CB = "ignore"

START_DATE_DAYS_AHEAD = 5