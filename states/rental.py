from aiogram.fsm.state import StatesGroup, State

class RentalCreateStates(StatesGroup):
    """Состояния процесса создания заявки на аренду."""

    period = State()  # Пользователь выбирает фиксированный диапазон аренды
    #quantity = State()  # Пользователь выбирает количество товара
    comment = State()  # Общий коммент пользователь
    confirmation = State()  # Пользователь подтверждает заявку