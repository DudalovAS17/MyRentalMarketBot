from aiogram.fsm.state import StatesGroup, State

class ProfileEditStates(StatesGroup):

    waiting_for_name = State()
    waiting_for_email = State()