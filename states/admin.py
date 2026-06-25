from aiogram.fsm.state import State, StatesGroup

class AdminStates(StatesGroup):

    # Rental request management
    waiting_rental_id = State()
    waiting_rental_cancel_reason = State()
    waiting_rental_reject_reason = State()

    # Catalog item management
    waiting_item_reject_reason = State()

    # Client account management
    waiting_user_id = State()
    waiting_user_ban_reason = State()