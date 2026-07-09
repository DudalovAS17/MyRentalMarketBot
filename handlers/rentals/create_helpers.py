
from handlers.rentals.rental_helpers.load import load_item_or_abort

from handlers.rentals.rental_helpers.texts import (not_item_id, not_item_for_rental, not_item, serv_item_err,
                                                   rental_data_err, not_all_rental_data_err, cancel_rent,
                                                   format_rent_confirmation_text, build_success_text, format_rent_confirmation_text,
                                                   format_rent_period_text, item_not_available_message, format_rent_comment_text,
                                                   format_rent_delivery_text, format_rent_quantity_text, format_rent_confirmation_text,
                                                   format_rent_client_name_text, format_rent_client_phone_text,
                                                   format_rent_delivery_address_text) # , format_rent_details_request_text
# serv_err_item, no_rent_data_err,

from handlers.rentals.rental_helpers.validate import (parse_rent_item_id, calculate_total_rent_price, calculate_price_for_fixed_period_total,
                                                      abort_if_item_unavailable, parse_rent_period_code, parse_rent_details_message,
                                                      parse_rent_quantity_code, parse_delivery_choice, parse_positive_int,
                                                      normalize_phone, is_quantity_available, is_rent_draft_complete)

from handlers.rentals.rental_helpers.keyboard import (build_rent_cancel_keyboard, build_rent_success_keyboard,
                                                      build_rent_period_keyboard, build_rent_comment_keyboard,
                                                      build_rent_delivery_keyboard, build_rent_quantity_keyboard,
                                                      build_rent_contact_keyboard, build_rent_confirmation_keyboard,
                                                      build_rent_step_keyboard, PERIOD_LABELS)

from handlers.rentals.rental_helpers.store import (get_rent_draft_context_or_abort, store_fixed_period_choice_and_price,
                                                   get_rent_draft_context_or_abort, store_rent_details_message, save_rent_draft)

#from handlers.rentals.rental_helpers.notif import notify_item_about_rent_request