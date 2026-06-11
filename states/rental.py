from aiogram.fsm.state import StatesGroup, State

class RentalCreateStates(StatesGroup):
    """Состояния процесса аренды"""

    start_date = State() # Пользователь выбирает дату начала
    end_date = State() # Пользователь выбирает дату окончания
    confirmation = State() # Подтверждение аренды