import logging
from aiogram.types import Message, CallbackQuery

logger = logging.getLogger(__name__)

def format_step(title: str, step: int, total: int) -> str:
    """Возвращает форматированный заголовок с прогрессом"""
    progress = f"<b>Шаг {step} из {total}</b>\n\n"
    return f"{progress}{title}"

