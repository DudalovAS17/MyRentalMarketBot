from aiogram.fsm.state import State, StatesGroup

class AdminStates(StatesGroup):
    waiting_rental_id = State()
    waiting_cancel_reason = State()
    waiting_dispute_resolution = State()
    waiting_dispute_target = State()
    waiting_item_reject_reason = State() # Admin item logic
    waiting_user_id = State() # Admin user logic
    waiting_user_ban_reason = State() # Admin user logic