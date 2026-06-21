
from handlers.rentals.rental_helpers.load import load_item_or_abort

from handlers.rentals.rental_helpers.texts import (not_item_id, not_item_for_rental, not_item, serv_item_err, rental_data_err,
                                                   not_all_rental_data_err, no_rent_data_err, cancel_rent,
                                                   format_rent_confirmation_text, build_success_text, format_rent_confirmation_text,
                                                   format_rent_period_text, item_not_available_message) # serv_err_item

from handlers.rentals.rental_helpers.validate import (parse_rent_item_id, calculate_total_rent_price, calculate_fixed_period_total,
                                                      ensure_rent_item_available_or_notify, parse_rent_period_code,)

from handlers.rentals.rental_helpers.keyboard import (build_rent_cancel_keyboard, build_rent_success_keyboard,
                                                      build_rent_period_keyboard, PERIOD_LABELS)

from handlers.rentals.rental_helpers.store import get_rent_confirm_context_or_abort, store_fixed_period_choice_and_price

#from handlers.rentals.rental_helpers.notif import notify_item_about_rent_request