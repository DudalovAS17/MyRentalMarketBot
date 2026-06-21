from aiogram.fsm.state import StatesGroup, State

class RentalCreateStates(StatesGroup):
    """Состояния процесса создания заявки на аренду."""

    period = State()  # Пользователь выбирает фиксированный диапазон аренды
    custom_dates = State()  # Пользователь вводит свои даты одним сообщением
    confirmation = State()  # Пользователь подтверждает заявку