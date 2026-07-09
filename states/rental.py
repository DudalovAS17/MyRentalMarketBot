from aiogram.fsm.state import StatesGroup, State

class RentalCreateStates(StatesGroup):
    """Состояния процесса создания заявки на аренду."""

    period = State()  # Пользователь выбирает фиксированный диапазон аренды
    quantity = State()  # Пользователь выбирает количество товара

    delivery_needed = State()
    delivery_address = State()

    client_name = State()
    client_phone = State()
    client_comment = State()

    confirmation = State()  # Пользователь подтверждает заявку