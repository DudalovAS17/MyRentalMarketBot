from typing import Optional
from aiogram.types import CallbackQuery


async def parse_int_id_from_callback(
    callback: CallbackQuery,
    index: int = 1,
    error_text: str = "Некорректные данные",
) -> Optional[int]:
    """
    Достаёт int ID из callback.data вида 'prefix:123'.
    При ошибке сам отвечает пользователю и возвращает None.
    """
    parts = callback.data.split(":")
    if len(parts) <= index:
        await callback.answer(error_text, show_alert=True)
        return None

    try:
        return int(parts[index])
    except ValueError:
        await callback.answer(error_text, show_alert=True)
        return None