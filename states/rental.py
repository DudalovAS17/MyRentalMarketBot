from aiogram.fsm.state import StatesGroup, State

class RentalCreateStates(StatesGroup):
    """Состояния процесса создания заявки на аренду."""

    period = State()  # Пользователь выбирает фиксированный диапазон аренды
    comment = State()  # Общий коммент пользователь
    confirmation = State()  # Пользователь подтверждает заявку