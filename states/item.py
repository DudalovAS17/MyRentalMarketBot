from aiogram.fsm.state import StatesGroup, State

class ItemCreateStates(StatesGroup):
    category = State()
    subcategory = State()
    title = State()
    description = State()
    price = State()
    deposit = State()
    location = State()
    rental_period = State()
    photos = State()
    confirmation = State()

