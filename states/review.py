from aiogram.fsm.state import StatesGroup, State

class ReviewStates(StatesGroup):
    rating = State()
    comment = State()
